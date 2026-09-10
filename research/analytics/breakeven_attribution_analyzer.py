"""
Product 04 — Research Laboratory: Breakeven 1R Paired Attribution Analyzer
Executes trade-level paired counterfactual attribution for HYP_MGT_BREAKEVEN_1R_01
against certified ANCHOR_2 baseline.
"""

import json
import os
from typing import Dict, List, Any

BASELINE_PATH = "/home/mrcn2/crypto-platform/scratch/anchor2_dev_certified_results.json"
TREATMENT_PATH = "/home/mrcn2/crypto-platform/scratch/breakeven_1r_dev_results.json"
OUTPUT_JSON_PATH = "/home/mrcn2/crypto-platform/scratch/breakeven_1r_paired_attribution.json"


def analyze_paired_attribution():
    with open(BASELINE_PATH, "r") as fp:
        baseline_payload = json.load(fp)
    with open(TREATMENT_PATH, "r") as fp:
        treatment_payload = json.load(fp)

    baseline_trades = baseline_payload.get("all_trades", [])
    treatment_trades = treatment_payload.get("all_trades", [])

    print(f"Loaded {len(baseline_trades)} baseline trades and {len(treatment_trades)} treatment trades.")

    # Sort both chronologically
    baseline_trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)
    treatment_trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)

    # Index treatment by trade_id
    treatment_by_id = {t["trade_id"]: t for t in treatment_trades}

    paired_records: List[Dict[str, Any]] = []

    # Counters
    losses_avoided_count = 0
    r_saved_from_losses = 0.0

    wins_sacrificed_count = 0
    r_sacrificed_from_winners = 0.0

    protected_losses = []
    improved_losses = []
    unaffected_losses = []
    preserved_winners = []
    sacrificed_winners = []
    reduced_winners = []

    for idx, b_t in enumerate(baseline_trades, 1):
        tid = b_t["trade_id"]
        t_t = treatment_by_id.get(tid)

        if not t_t:
            raise RuntimeError(f"FATAL: Baseline trade {tid} missing in treatment!")

        symbol = b_t.get("symbol")
        tf_set = b_t.get("timeframe_set")
        direction = b_t.get("directional_permission")
        entry_ts = b_t.get("entry_timestamp")

        b_net_r = float(b_t.get("realized_r") or b_t.get("realized_rr") or 0.0)
        t_net_r = float(t_t.get("realized_r") or t_t.get("realized_rr") or 0.0)
        delta_r = t_net_r - b_net_r

        b_mfe = float(b_t.get("mfe_r", 0.0))
        b_mae = float(b_t.get("mae_r", 0.0))
        t_mfe = float(t_t.get("mfe_r", 0.0))
        t_mae = float(t_t.get("mae_r", 0.0))

        b_exit_reason = b_t.get("exit_reason")
        t_exit_reason = t_t.get("exit_reason")

        be_triggered = bool(t_t.get("metadata", {}).get("breakeven_triggered", False))
        be_trig_ts = t_t.get("metadata", {}).get("breakeven_trigger_ts")
        be_trig_price = t_t.get("metadata", {}).get("breakeven_trigger_price")
        be_stop_ts = t_t.get("metadata", {}).get("breakeven_stop_ts")
        be_stop_price = t_t.get("metadata", {}).get("breakeven_stop_price")

        # Classify outcome
        outcome_cat = "UNCHANGED"
        if abs(delta_r) < 1e-4:
            if b_net_r > 0:
                outcome_cat = "PRESERVED_WINNER"
                preserved_winners.append(tid)
            else:
                outcome_cat = "UNAFFECTED_LOSS"
                unaffected_losses.append(tid)
        elif b_net_r < 0:
            if t_net_r > 0:
                outcome_cat = "PROTECTED_LOSS"
                protected_losses.append(tid)
                r_saved_from_losses += delta_r
                losses_avoided_count += 1
            elif t_net_r > b_net_r:
                outcome_cat = "IMPROVED_LOSS"
                improved_losses.append(tid)
                r_saved_from_losses += delta_r
                losses_avoided_count += 1
            else:
                outcome_cat = "WORSENED_LOSS"
        else: # b_net_r > 0
            if t_net_r <= 0:
                outcome_cat = "SACRIFICED_WINNER"
                sacrificed_winners.append(tid)
                r_sacrificed_from_winners += abs(delta_r)
                wins_sacrificed_count += 1
            elif t_net_r < b_net_r - 0.01:
                outcome_cat = "REDUCED_WINNER"
                reduced_winners.append(tid)
                r_sacrificed_from_winners += abs(delta_r)
            else:
                outcome_cat = "PRESERVED_WINNER"
                preserved_winners.append(tid)

        record = {
            "baseline_trade_num": idx,
            "trade_id": tid,
            "symbol": symbol,
            "timeframe_set": tf_set,
            "direction": direction,
            "entry_timestamp": entry_ts,
            "baseline_net_r": round(b_net_r, 4),
            "treatment_net_r": round(t_net_r, 4),
            "delta_r": round(delta_r, 4),
            "baseline_mfe": round(b_mfe, 2),
            "baseline_mae": round(b_mae, 2),
            "treatment_mfe": round(t_mfe, 2),
            "treatment_mae": round(t_mae, 2),
            "baseline_exit_reason": b_exit_reason,
            "treatment_exit_reason": t_exit_reason,
            "breakeven_triggered": be_triggered,
            "breakeven_trigger_ts": be_trig_ts,
            "breakeven_trigger_price": be_trig_price,
            "breakeven_stop_ts": be_stop_ts,
            "breakeven_stop_price": be_stop_price,
            "outcome_category": outcome_cat,
            "is_runner_1r": b_mfe >= 1.0,
            "baseline_giveback": round(b_mfe - b_net_r, 4),
            "treatment_giveback": round(t_mfe - t_net_r, 4)
        }
        paired_records.append(record)

    # Aggregate performance
    b_agg = baseline_payload.get("aggregate_performance", {})
    t_agg = treatment_payload.get("aggregate_performance", {})

    # Runner analysis (MFE >= 1.0R)
    runners = [r for r in paired_records if r["is_runner_1r"]]

    efficiency_ratio = (
        (r_saved_from_losses / r_sacrificed_from_winners)
        if r_sacrificed_from_winners > 0
        else (999.0 if r_saved_from_losses > 0 else 0.0)
    )

    summary = {
        "baseline_metrics": b_agg,
        "treatment_metrics": t_agg,
        "delta_metrics": {
            "net_r": round(t_agg.get("net_r", 0.0) - b_agg.get("net_r", 0.0), 4),
            "expectancy": round(t_agg.get("expectancy", 0.0) - b_agg.get("expectancy", 0.0), 4),
            "profit_factor": round(t_agg.get("profit_factor", 0.0) - b_agg.get("profit_factor", 0.0), 4),
            "max_drawdown_r": round(t_agg.get("max_drawdown_r", 0.0) - b_agg.get("max_drawdown_r", 0.0), 4),
            "wins_delta": t_agg.get("wins", 0) - b_agg.get("wins", 0),
            "losses_delta": t_agg.get("losses", 0) - b_agg.get("losses", 0)
        },
        "attribution_accounting": {
            "total_trades": len(paired_records),
            "runners_count": len(runners),
            "breakeven_triggered_count": sum(1 for r in paired_records if r["breakeven_triggered"]),
            "losses_improved_or_protected_count": losses_avoided_count,
            "r_saved_from_losses": round(r_saved_from_losses, 4),
            "wins_sacrificed_count": wins_sacrificed_count,
            "r_sacrificed_from_winners": round(r_sacrificed_from_winners, 4),
            "efficiency_ratio": round(efficiency_ratio, 2),
            "categories": {
                "protected_losses": protected_losses,
                "improved_losses": improved_losses,
                "unaffected_losses": unaffected_losses,
                "preserved_winners": preserved_winners,
                "sacrificed_winners": sacrificed_winners,
                "reduced_winners": reduced_winners
            }
        },
        "runners_detailed": runners,
        "all_paired_trades": paired_records
    }

    with open(OUTPUT_JSON_PATH, "w") as fp:
        json.dump(summary, fp, indent=2)

    print("\n" + "=" * 80)
    print(f"PAIRED ATTRIBUTION COMPLETE: Saved to {OUTPUT_JSON_PATH}")
    print(f"Baseline Net R: {b_agg.get('net_r'):.4f}R -> Treatment Net R: {t_agg.get('net_r'):.4f}R (Delta: {summary['delta_metrics']['net_r']:+.4f}R)")
    print(f"Expectancy: {b_agg.get('expectancy'):.4f}R -> {t_agg.get('expectancy'):.4f}R (Delta: {summary['delta_metrics']['expectancy']:+.4f}R)")
    print(f"Profit Factor: {b_agg.get('profit_factor'):.4f} -> {t_agg.get('profit_factor'):.4f}")
    print(f"Max DD: {b_agg.get('max_drawdown_r'):.4f}R -> {t_agg.get('max_drawdown_r'):.4f}R")
    print(f"Runners (MFE >= 1.0R): {len(runners)} / 23")
    print(f"R Saved from Losses: +{r_saved_from_losses:.4f}R")
    print(f"R Sacrificed from Winners: -{r_sacrificed_from_winners:.4f}R")
    print(f"Efficiency Ratio: {efficiency_ratio:.2f}x")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    analyze_paired_attribution()
