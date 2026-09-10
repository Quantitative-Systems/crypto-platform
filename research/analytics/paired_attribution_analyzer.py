"""
Product 04 — Research Analytics: Paired Attribution Analyzer
Performs 1-to-1 paired trade-level forensic accounting comparing:
  - Baseline Control: ANCHOR_2 (N=23 certified trades)
  - Treatment: HYP_ENTRY_DISPLACEMENT_POLARITY_01

Accounts for every baseline trade:
  - RETAINED vs FILTERED
  - Losses Avoided vs Wins Sacrificed
  - Emergent New Trades
  - Net Delta R Attribution
  - Formal Institutional Gate Verdict (A, B, C, D, E)
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/home/mrcn2/crypto-platform")


class PairedAttributionAnalyzer:

    @staticmethod
    def analyze(baseline_path: str, treatment_path: str) -> Dict[str, Any]:
        with open(baseline_path, "r") as fb:
            baseline_data = json.load(fb)
        with open(treatment_path, "r") as ft:
            treatment_data = json.load(ft)

        base_trades = baseline_data["all_trades"]
        treat_trades = treatment_data["all_trades"]

        base_trade_map = {t["trade_id"]: t for t in base_trades}
        treat_trade_map = {t["trade_id"]: t for t in treat_trades}

        retained_trades = []
        filtered_losses = []
        filtered_wins = []
        newly_emerged_trades = []

        # 1. Map each baseline trade
        paired_records = []
        for i, bt in enumerate(base_trades):
            tid = bt["trade_id"]
            pnl_base = bt["net_r"]
            mfe_base = bt.get("mfe_r", 0.0)
            mae_base = bt.get("mae_r", 0.0)
            ex_base = bt.get("exit_reason", "")
            is_win = pnl_base > 0

            if tid in treat_trade_map:
                tt = treat_trade_map[tid]
                pnl_treat = tt["net_r"]
                mfe_treat = tt.get("mfe_r", 0.0)
                mae_treat = tt.get("mae_r", 0.0)
                ex_treat = tt.get("exit_reason", "")
                status = "RETAINED"
                retained_trades.append({
                    "trade_id": tid,
                    "baseline": bt,
                    "treatment": tt,
                    "delta_pnl_r": round(pnl_treat - pnl_base, 4)
                })
                paired_records.append({
                    "index": i + 1,
                    "trade_id": tid,
                    "symbol": bt["symbol"],
                    "timeframe_set": bt["timeframe_set"],
                    "status": "RETAINED",
                    "baseline_pnl_r": pnl_base,
                    "treatment_pnl_r": pnl_treat,
                    "baseline_mfe_r": mfe_base,
                    "treatment_mfe_r": mfe_treat,
                    "baseline_exit": ex_base,
                    "treatment_exit": ex_treat,
                    "delta_r": round(pnl_treat - pnl_base, 4)
                })
            else:
                status = "FILTERED"
                delta_r = -pnl_base  # If loss was -1R, delta is +1R avoided; if win +2R, delta is -2R lost
                record = {
                    "index": i + 1,
                    "trade_id": tid,
                    "symbol": bt["symbol"],
                    "timeframe_set": bt["timeframe_set"],
                    "status": "FILTERED",
                    "baseline_pnl_r": pnl_base,
                    "treatment_pnl_r": 0.0,
                    "baseline_mfe_r": mfe_base,
                    "treatment_mfe_r": 0.0,
                    "baseline_exit": ex_base,
                    "treatment_exit": "REJECT_ENTRY_DISPLACEMENT_POLARITY",
                    "delta_r": round(delta_r, 4)
                }
                paired_records.append(record)
                if is_win:
                    filtered_wins.append(bt)
                else:
                    filtered_losses.append(bt)

        # 2. Check for newly emerged trades in treatment
        for tt in treat_trades:
            tid = tt["trade_id"]
            if tid not in base_trade_map:
                newly_emerged_trades.append(tt)

        # 3. Delta Accounting Calculations
        losses_avoided_count = len(filtered_losses)
        losses_avoided_r = sum(abs(t["net_r"]) for t in filtered_losses)

        wins_sacrificed_count = len(filtered_wins)
        wins_sacrificed_r = sum(t["net_r"] for t in filtered_wins)

        new_trades_count = len(newly_emerged_trades)
        new_trades_net_r = sum(t["net_r"] for t in newly_emerged_trades)

        net_delta_from_filtering = losses_avoided_r - wins_sacrificed_r
        total_net_delta_r = net_delta_from_filtering + new_trades_net_r

        efficiency_ratio = (losses_avoided_r / wins_sacrificed_r) if wins_sacrificed_r > 0 else (999.0 if losses_avoided_r > 0 else 0.0)

        # 4. Immediate Invalidation Shift (<0.5R MFE)
        base_imm_inv = [t for t in base_trades if t["net_r"] < 0 and t.get("mfe_r", 0.0) < 0.5]
        base_imm_inv_count = len(base_imm_inv)
        filtered_imm_inv = [t for t in filtered_losses if t.get("mfe_r", 0.0) < 0.5]
        filtered_imm_inv_count = len(filtered_imm_inv)

        # 5. Aggregate metrics comparison
        base_agg = baseline_data["aggregate_performance"]
        treat_agg = treatment_data["aggregate_performance"]

        # 6. Formal Institutional Gate Classification
        # Result A: Losses reduced materially, 0 or minimal winners sacrificed, expectancy improves significantly
        # Result B: Expectancy improves, but remains negative
        # Result C: Neutral (minimal delta)
        # Result D: Harmful (winners killed, expectancy drops)
        # Result E: Implementation defect
        if treat_agg["total_trades"] == 0:
            verdict = "RESULT_D_HARMFUL"
            verdict_rationale = "Filter eliminated all trades in the dataset."
        elif wins_sacrificed_r > losses_avoided_r:
            verdict = "RESULT_D_HARMFUL"
            verdict_rationale = f"Filter destroyed more winning R ({wins_sacrificed_r:.4f}R) than losses avoided ({losses_avoided_r:.4f}R)."
        elif treat_agg["expectancy"] > 0:
            verdict = "RESULT_A_STRONG_POSITIVE_EVIDENCE"
            verdict_rationale = f"Expectancy turned positive ({treat_agg['expectancy']:.4f}R) with favorable efficiency ratio {efficiency_ratio:.2f}x."
        elif treat_agg["expectancy"] > base_agg["expectancy"]:
            verdict = "RESULT_B_IMPROVEMENT_BUT_INSUFFICIENT"
            verdict_rationale = f"Expectancy improved from {base_agg['expectancy']:.4f}R to {treat_agg['expectancy']:.4f}R, but remains negative."
        elif abs(treat_agg["expectancy"] - base_agg["expectancy"]) < 0.02:
            verdict = "RESULT_C_NEUTRAL"
            verdict_rationale = f"No meaningful economic differentiation (Expectancy delta < 0.02R)."
        else:
            verdict = "RESULT_D_HARMFUL"
            verdict_rationale = f"Expectancy deteriorated from {base_agg['expectancy']:.4f}R to {treat_agg['expectancy']:.4f}R."

        return {
            "summary": {
                "baseline_total_trades": len(base_trades),
                "treatment_total_trades": len(treat_trades),
                "retained_trades_count": len(retained_trades),
                "filtered_losses_count": losses_avoided_count,
                "filtered_losses_avoided_r": round(losses_avoided_r, 4),
                "filtered_wins_count": wins_sacrificed_count,
                "filtered_wins_sacrificed_r": round(wins_sacrificed_r, 4),
                "new_trades_count": new_trades_count,
                "new_trades_net_r": round(new_trades_net_r, 4),
                "net_delta_from_filtering_r": round(net_delta_from_filtering, 4),
                "total_net_delta_r": round(total_net_delta_r, 4),
                "efficiency_ratio": round(efficiency_ratio, 2),
                "immediate_invalidations_baseline": base_imm_inv_count,
                "immediate_invalidations_filtered": filtered_imm_inv_count,
                "immediate_invalidations_retained": base_imm_inv_count - filtered_imm_inv_count,
                "verdict": verdict,
                "verdict_rationale": verdict_rationale
            },
            "aggregate_comparison": {
                "baseline": base_agg,
                "treatment": treat_agg,
                "delta": {
                    "net_r": round(treat_agg["net_r"] - base_agg["net_r"], 4),
                    "expectancy": round(treat_agg["expectancy"] - base_agg["expectancy"], 4),
                    "win_rate": round(treat_agg["win_rate"] - base_agg["win_rate"], 2),
                    "profit_factor": round(treat_agg["profit_factor"] - base_agg["profit_factor"], 4),
                    "max_drawdown_r": round(treat_agg["max_drawdown_r"] - base_agg["max_drawdown_r"], 4)
                }
            },
            "paired_records": paired_records,
            "newly_emerged_trades": newly_emerged_trades
        }

    @staticmethod
    def format_report(analysis: Dict[str, Any]) -> str:
        s = analysis["summary"]
        ac = analysis["aggregate_comparison"]
        records = analysis["paired_records"]
        new_trades = analysis["newly_emerged_trades"]

        lines = []
        lines.append("# PAIRED TRADE-LEVEL ATTRIBUTION REPORT")
        lines.append("## HYP_ENTRY_DISPLACEMENT_POLARITY_01 vs ANCHOR_2 BASELINE\n")

        lines.append("### 1. Headline Delta Summary")
        lines.append(f"- **Verdict:** `{s['verdict']}`")
        lines.append(f"- **Rationale:** {s['verdict_rationale']}")
        lines.append(f"- **Baseline Population:** {s['baseline_total_trades']} trades | **Treatment Population:** {s['treatment_total_trades']} trades")
        lines.append(f"- **Retained Baseline Trades:** {s['retained_trades_count']} / {s['baseline_total_trades']}")
        lines.append(f"- **Filtered Losses Avoided:** {s['filtered_losses_count']} trades (+{s['filtered_losses_avoided_r']:.4f}R avoided)")
        lines.append(f"- **Filtered Wins Sacrificed:** {s['filtered_wins_count']} trades (-{s['filtered_wins_sacrificed_r']:.4f}R lost)")
        lines.append(f"- **Efficiency Ratio:** {s['efficiency_ratio']}x (Losses Avoided R / Wins Sacrificed R)")
        lines.append(f"- **Net Filtering Impact:** {s['net_delta_from_filtering_r']:+.4f}R")
        lines.append(f"- **Newly Emerged Trades:** {s['new_trades_count']} trades ({s['new_trades_net_r']:+.4f}R)")
        lines.append(f"- **Total Net R Delta:** {s['total_net_delta_r']:+.4f}R")
        lines.append(f"- **Immediate Invalidations (<0.5R MFE):** Filtered {s['immediate_invalidations_filtered']} / {s['immediate_invalidations_baseline']} ({s['immediate_invalidations_filtered'] / s['immediate_invalidations_baseline'] * 100:.1f}% removed)\n")

        lines.append("### 2. Aggregate Performance Comparison")
        lines.append("| Metric | Baseline (ANCHOR_2) | Treatment (POLARITY_01) | Delta |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| Total Trades | {ac['baseline']['total_trades']} | {ac['treatment']['total_trades']} | {ac['treatment']['total_trades'] - ac['baseline']['total_trades']} |")
        lines.append(f"| Win Rate | {ac['baseline']['win_rate']:.2f}% | {ac['treatment']['win_rate']:.2f}% | {ac['delta']['win_rate']:+.2f}% |")
        lines.append(f"| Net PnL (R) | {ac['baseline']['net_r']:+.4f}R | {ac['treatment']['net_r']:+.4f}R | {ac['delta']['net_r']:+.4f}R |")
        lines.append(f"| Expectancy | {ac['baseline']['expectancy']:+.4f}R | {ac['treatment']['expectancy']:+.4f}R | {ac['delta']['expectancy']:+.4f}R |")
        lines.append(f"| Profit Factor | {ac['baseline']['profit_factor']:.4f} | {ac['treatment']['profit_factor']:.4f} | {ac['delta']['profit_factor']:+.4f} |")
        lines.append(f"| Max Drawdown | {ac['baseline']['max_drawdown_r']:.4f}R | {ac['treatment']['max_drawdown_r']:.4f}R | {ac['delta']['max_drawdown_r']:+.4f}R |\n")

        lines.append("### 3. Paired Trade-by-Trade Matrix (All 23 Baseline Trades)")
        lines.append("| # | Trade ID | Symbol | Set | Status | Baseline Net R | Treatment Net R | Delta R | Baseline MFE | Exit Reason |")
        lines.append("| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in records:
            lines.append(f"| {r['index']:02d} | `{r['trade_id']}` | {r['symbol']} | {r['timeframe_set']} | **{r['status']}** | {r['baseline_pnl_r']:+.4f}R | {r['treatment_pnl_r']:+.4f}R | {r['delta_r']:+.4f}R | {r['baseline_mfe_r']:.2f}R | {r['baseline_exit']} |")

        if new_trades:
            lines.append("\n### 4. Newly Emerged Trades in Treatment")
            lines.append("| Trade ID | Symbol | Set | Net R | MFE | MAE | Exit Reason |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for nt in new_trades:
                lines.append(f"| `{nt['trade_id']}` | {nt['symbol']} | {nt['timeframe_set']} | {nt['net_r']:+.4f}R | {nt.get('mfe_r', 0):.2f}R | {nt.get('mae_r', 0):.2f}R | {nt.get('exit_reason')} |")

        return "\n".join(lines)


if __name__ == "__main__":
    baseline = "/home/mrcn2/crypto-platform/scratch/anchor2_dev_certified_results.json"
    treatment = "/home/mrcn2/crypto-platform/scratch/polarity_dev_results.json"
    if os.path.exists(treatment):
        res = PairedAttributionAnalyzer.analyze(baseline, treatment)
        report = PairedAttributionAnalyzer.format_report(res)
        print(report)
        with open("/home/mrcn2/crypto-platform/scratch/paired_attribution_results.json", "w") as fp:
            json.dump(res, fp, indent=2)
    else:
        print(f"Treatment file not found: {treatment}")
