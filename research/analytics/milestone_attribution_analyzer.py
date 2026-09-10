"""
Research Cycle #4 Analytics: Milestone Attribution Analyzer
HYP_TARGET_MILESTONE_01 (+2.5R Milestone Target Exit)

Compares frozen COMPOSITE_01 baseline vs MILESTONE_2_5R treatment across all 13 trades:
- Exact trade-by-trade paired attribution
- Excursion and giveback comparison
- Runner convexity analysis (#05 and #10)
- Convexity sacrifice vs giveback preservation quantification
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional


def match_trade(trade_ref: Dict[str, Any], trade_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    t_id = trade_ref.get("trade_id")
    for t in trade_list:
        if t.get("trade_id") == t_id:
            return t
            
    ref_stream = trade_ref.get("stream_id")
    ref_setup = trade_ref.get("setup_timestamp")
    ref_entry = trade_ref.get("entry_timestamp")
    
    for t in trade_list:
        if t.get("stream_id") == ref_stream:
            if ref_setup and t.get("setup_timestamp") == ref_setup:
                return t
            if ref_entry and t.get("entry_timestamp") == ref_entry:
                return t
    return None


def run_milestone_attribution(
    composite_path: str = "/home/mrcn2/crypto-platform/scratch/composite_01_dev_results.json",
    milestone_path: str = "/home/mrcn2/crypto-platform/scratch/milestone_2_5r_dev_results.json",
    output_path: str = "/home/mrcn2/crypto-platform/scratch/milestone_2_5r_attribution.json"
) -> Dict[str, Any]:
    with open(composite_path, "r") as fp:
        comp_data = json.load(fp)
    with open(milestone_path, "r") as fp:
        ms_data = json.load(fp)

    comp_trades = comp_data.get("all_trades", [])
    ms_trades = ms_data.get("all_trades", [])

    comp_trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)

    rows = []
    total_gained_r = 0.0
    total_sacrificed_r = 0.0
    net_delta_r = 0.0

    improved_trades = []
    unchanged_trades = []
    harmed_trades = []
    truncated_runners = []
    sub_2_5r_trades = []

    for idx, c_trade in enumerate(comp_trades, 1):
        trade_id = c_trade.get("trade_id")
        stream_id = c_trade.get("stream_id")
        direction = "LONG" if "LONG" in str(c_trade.get("directional_permission", c_trade.get("direction"))) else "SHORT"
        
        c_realized_r = float(c_trade.get("realized_r", c_trade.get("realized_rr", 0.0)))
        c_mfe_r = float(c_trade.get("mfe_r", 0.0))
        c_mae_r = float(c_trade.get("mae_r", 0.0))
        c_exit_reason = c_trade.get("exit_reason", "UNKNOWN")

        ms_match = match_trade(c_trade, ms_trades)
        if not ms_match:
            print(f"❌ ERROR: Missing match in treatment for trade {trade_id}")
            continue

        ms_realized_r = float(ms_match.get("realized_r", ms_match.get("realized_rr", 0.0)))
        ms_exit_reason = ms_match.get("exit_reason", "UNKNOWN")
        delta_r = ms_realized_r - c_realized_r
        net_delta_r += delta_r

        mfe_ge_2_5 = (c_mfe_r >= 2.5)
        milestone_triggered = (ms_exit_reason == "MILESTONE_TARGET_EXIT")

        if not mfe_ge_2_5:
            sub_2_5r_trades.append(trade_id)

        if abs(delta_r) < 1e-4:
            cat = "UNCHANGED"
            unchanged_trades.append(trade_id)
        elif delta_r > 0:
            cat = "IMPROVED"
            total_gained_r += delta_r
            improved_trades.append(trade_id)
        else:
            cat = "HARMED_CONVEXITY_TRUNCATED"
            total_sacrificed_r += abs(delta_r)
            harmed_trades.append(trade_id)
            if milestone_triggered:
                truncated_runners.append(trade_id)

        rows.append({
            "index": idx,
            "trade_id": trade_id,
            "stream_id": stream_id,
            "direction": direction,
            "baseline_mfe_r": round(c_mfe_r, 4),
            "baseline_mae_r": round(c_mae_r, 4),
            "baseline_realized_r": round(c_realized_r, 4),
            "baseline_exit_reason": c_exit_reason,
            "treatment_realized_r": round(ms_realized_r, 4),
            "treatment_exit_reason": ms_exit_reason,
            "delta_r": round(delta_r, 4),
            "mfe_reached_2_5r": mfe_ge_2_5,
            "milestone_triggered": milestone_triggered,
            "category": cat
        })

    comp_perf = comp_data.get("aggregate_performance", {})
    ms_perf = ms_data.get("aggregate_performance", {})

    summary = {
        "experiment_id": "HYP_TARGET_MILESTONE_01",
        "parent_baseline": "HYP_COMPOSITE_POLARITY_BREAKEVEN_01",
        "population_counts": {
            "composite_baseline_n": len(comp_trades),
            "milestone_treatment_n": len(ms_trades),
            "delta_n": len(ms_trades) - len(comp_trades)
        },
        "convexity_accounting": {
            "total_r_gained_from_improved_exits": round(total_gained_r, 4),
            "total_r_sacrificed_from_truncated_winners": round(total_sacrificed_r, 4),
            "net_delta_r": round(net_delta_r, 4),
            "improved_count": len(improved_trades),
            "unchanged_count": len(unchanged_trades),
            "harmed_count": len(harmed_trades),
            "truncated_runners_count": len(truncated_runners),
            "sub_2_5r_count": len(sub_2_5r_trades)
        },
        "performance_comparison": {
            "composite_baseline": comp_perf,
            "milestone_treatment": ms_perf,
            "delta": {
                "net_r": round(ms_perf.get("net_r", 0.0) - comp_perf.get("net_r", 0.0), 4),
                "expectancy": round(ms_perf.get("expectancy", 0.0) - comp_perf.get("expectancy", 0.0), 4),
                "profit_factor": round(ms_perf.get("profit_factor", 0.0) - comp_perf.get("profit_factor", 0.0), 4),
                "max_drawdown_r": round(ms_perf.get("max_drawdown_r", 0.0) - comp_perf.get("max_drawdown_r", 0.0), 4),
                "win_rate": round(ms_perf.get("win_rate", 0.0) - comp_perf.get("win_rate", 0.0), 2)
            }
        },
        "rows": rows
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fp:
        json.dump(summary, fp, indent=2)

    print("\n" + "="*80)
    print("MILESTONE ATTRIBUTION ANALYSIS COMPLETE")
    print(f"Population: Baseline N={len(comp_trades)} | Treatment N={len(ms_trades)}")
    print(f"Net Realized R: Base={comp_perf.get('net_r')}R -> Treatment={ms_perf.get('net_r')}R (Delta: {summary['performance_comparison']['delta']['net_r']:+.4f}R)")
    print(f"Expectancy: Base={comp_perf.get('expectancy')}R -> Treatment={ms_perf.get('expectancy')}R (Delta: {summary['performance_comparison']['delta']['expectancy']:+.4f}R)")
    print(f"Total R Gained: +{total_gained_r:.4f}R | Total R Sacrificed: -{total_sacrificed_r:.4f}R | Net Delta: {net_delta_r:+.4f}R")
    print(f"Trade Breakdown: Improved={len(improved_trades)}, Harmed={len(harmed_trades)}, Unchanged={len(unchanged_trades)}")
    print("="*80)
    return summary


if __name__ == "__main__":
    run_milestone_attribution()
