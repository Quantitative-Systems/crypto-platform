"""
Product 04 — Research Analytics: Composite Interaction Analyzer
Cycle #3: HYP_COMPOSITE_POLARITY_BREAKEVEN_01

Evaluates the controlled interaction / composition of:
  - Branch 1: Entry Displacement Polarity (HYP_ENTRY_DISPLACEMENT_POLARITY_01)
  - Branch 2: +1.0R Breakeven Ratchet (HYP_MGT_BREAKEVEN_1R_01)

Implements rigorous accounting mathematics:
  Delta P_i = P_i - B_i
  Delta B_i = BE_i - B_i
  Delta C_i = C_i - B_i
  I_i       = Delta C_i - (Delta P_i + Delta B_i)
  I_total   = Sum_{i=1}^{23} I_i

Maintains explicit separation:
  - status: RETAINED / FILTERED / UNCHANGED / PROTECTED / IMPROVED / SACRIFICED / NEW / ALTERED
  - accounting R: 0.0R counterfactual contribution for filtered opportunities
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional


def match_trade(trade_ref: Dict[str, Any], trade_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Match trade by trade_id, or fallback to stream_id and setup_timestamp."""
    t_id = trade_ref.get("trade_id")
    for t in trade_list:
        if t.get("trade_id") == t_id:
            return t
            
    # Fallback to stream_id + setup_timestamp
    ref_stream = trade_ref.get("stream_id")
    ref_setup = trade_ref.get("setup_timestamp")
    ref_entry_ts = trade_ref.get("entry_timestamp")
    
    for t in trade_list:
        if t.get("stream_id") == ref_stream:
            if ref_setup and t.get("setup_timestamp") == ref_setup:
                return t
            if ref_entry_ts and t.get("entry_timestamp") == ref_entry_ts:
                return t
    return None


def run_interaction_analysis(
    baseline_path: str = "/home/mrcn2/crypto-platform/scratch/anchor2_dev_certified_results.json",
    polarity_path: str = "/home/mrcn2/crypto-platform/scratch/polarity_dev_results.json",
    breakeven_path: str = "/home/mrcn2/crypto-platform/scratch/breakeven_1r_dev_results.json",
    composite_path: str = "/home/mrcn2/crypto-platform/scratch/composite_01_dev_results.json",
    output_path: str = "/home/mrcn2/crypto-platform/scratch/composite_interaction_results.json"
) -> Dict[str, Any]:
    
    with open(baseline_path, "r") as fp:
        baseline_data = json.load(fp)
    with open(polarity_path, "r") as fp:
        polarity_data = json.load(fp)
    with open(breakeven_path, "r") as fp:
        breakeven_data = json.load(fp)
    with open(composite_path, "r") as fp:
        composite_data = json.load(fp)

    base_trades = baseline_data.get("all_trades", [])
    pol_trades = polarity_data.get("all_trades", [])
    be_trades = breakeven_data.get("all_trades", [])
    comp_trades = composite_data.get("all_trades", [])

    # Sort baseline trades chronologically
    base_trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)

    matrix_rows = []
    total_delta_p = 0.0
    total_delta_be = 0.0
    total_delta_c = 0.0
    total_interaction = 0.0

    matched_comp_ids = set()

    for idx, b_trade in enumerate(base_trades, 1):
        trade_id = b_trade.get("trade_id")
        stream_id = b_trade.get("stream_id")
        direction = b_trade.get("directional_permission")
        entry_ts = b_trade.get("entry_timestamp")
        
        b_realized_r = float(b_trade.get("realized_r", b_trade.get("realized_rr", 0.0)))
        b_exit_reason = b_trade.get("exit_reason", "UNKNOWN")

        # 1. Polarity Branch
        pol_match = match_trade(b_trade, pol_trades)
        if pol_match:
            pol_status = "RETAINED"
            pol_exec_r = float(pol_match.get("realized_r", pol_match.get("realized_rr", 0.0)))
            pol_accounting_r = pol_exec_r
            pol_exit_reason = pol_match.get("exit_reason", "UNKNOWN")
        else:
            pol_status = "FILTERED"
            pol_exec_r = None
            pol_accounting_r = 0.0  # Counterfactual contribution
            pol_exit_reason = "ENTRY_FILTERED"

        delta_p = pol_accounting_r - b_realized_r
        total_delta_p += delta_p

        # 2. Breakeven Branch
        be_match = match_trade(b_trade, be_trades)
        if be_match:
            be_exec_r = float(be_match.get("realized_r", be_match.get("realized_rr", 0.0)))
            be_accounting_r = be_exec_r
            be_exit_reason = be_match.get("exit_reason", "UNKNOWN")
            
            diff_be = be_exec_r - b_realized_r
            if abs(diff_be) < 1e-4:
                be_status = "UNCHANGED"
            elif diff_be > 0:
                if b_realized_r < 0 and be_exec_r >= 0:
                    be_status = "PROTECTED"
                else:
                    be_status = "IMPROVED"
            else:
                be_status = "SACRIFICED"
        else:
            be_status = "MISSING_ERROR"
            be_exec_r = None
            be_accounting_r = 0.0
            be_exit_reason = "MISSING"

        delta_be = be_accounting_r - b_realized_r
        total_delta_be += delta_be

        # 3. Composite Branch
        comp_match = match_trade(b_trade, comp_trades)
        if comp_match:
            matched_comp_ids.add(comp_match.get("trade_id"))
            comp_exec_r = float(comp_match.get("realized_r", comp_match.get("realized_rr", 0.0)))
            comp_accounting_r = comp_exec_r
            comp_exit_reason = comp_match.get("exit_reason", "UNKNOWN")
            
            # Check if altered vs polarity retained
            if pol_match and abs(comp_exec_r - pol_exec_r) < 1e-4 and comp_exit_reason == pol_exit_reason:
                comp_status = "RETAINED_UNCHANGED"
            elif pol_match and comp_exec_r > pol_exec_r:
                comp_status = "RETAINED_IMPROVED"
            elif pol_match and comp_exec_r < pol_exec_r:
                comp_status = "RETAINED_DEGRADED"
            else:
                comp_status = "RETAINED"
        else:
            comp_status = "FILTERED"
            comp_exec_r = None
            comp_accounting_r = 0.0
            comp_exit_reason = "ENTRY_FILTERED"

        delta_c = comp_accounting_r - b_realized_r
        total_delta_c += delta_c

        interaction_i = delta_c - (delta_p + delta_be)
        total_interaction += interaction_i

        matrix_rows.append({
            "index": idx,
            "trade_id": trade_id,
            "stream_id": stream_id,
            "direction": direction,
            "entry_timestamp": entry_ts,
            # Baseline
            "b_realized_r": round(b_realized_r, 4),
            "b_exit_reason": b_exit_reason,
            # Polarity
            "pol_status": pol_status,
            "pol_exec_r": round(pol_exec_r, 4) if pol_exec_r is not None else None,
            "pol_accounting_r": round(pol_accounting_r, 4),
            "pol_exit_reason": pol_exit_reason,
            "delta_p": round(delta_p, 4),
            # Breakeven
            "be_status": be_status,
            "be_exec_r": round(be_exec_r, 4) if be_exec_r is not None else None,
            "be_accounting_r": round(be_accounting_r, 4),
            "be_exit_reason": be_exit_reason,
            "delta_be": round(delta_be, 4),
            # Composite
            "comp_status": comp_status,
            "comp_exec_r": round(comp_exec_r, 4) if comp_exec_r is not None else None,
            "comp_accounting_r": round(comp_accounting_r, 4),
            "comp_exit_reason": comp_exit_reason,
            "delta_c": round(delta_c, 4),
            # Interaction
            "interaction_i": round(interaction_i, 4)
        })

    # Check for unmatched / new trades in Composite
    unmatched_comp_trades = []
    for ct in comp_trades:
        if ct.get("trade_id") not in matched_comp_ids:
            # Try to see if it matches any base trade
            if not match_trade(ct, base_trades):
                unmatched_comp_trades.append(ct)

    comp_perf = composite_data.get("aggregate_performance", {})
    base_perf = baseline_data.get("aggregate_performance", {})
    pol_perf = polarity_data.get("aggregate_performance", {})
    be_perf = breakeven_data.get("aggregate_performance", {})

    summary = {
        "experiment_id": "HYP_COMPOSITE_POLARITY_BREAKEVEN_01",
        "reference_baseline_n": len(base_trades),
        "executed_counts": {
            "baseline_n": len(base_trades),
            "polarity_n": len(pol_trades),
            "breakeven_n": len(be_trades),
            "composite_n": len(comp_trades),
            "unmatched_new_trades_n": len(unmatched_comp_trades)
        },
        "aggregate_performance": {
            "baseline": base_perf,
            "polarity": pol_perf,
            "breakeven": be_perf,
            "composite": comp_perf
        },
        "interaction_accounting": {
            "total_delta_p_r": round(total_delta_p, 4),
            "total_delta_be_r": round(total_delta_be, 4),
            "total_delta_c_r": round(total_delta_c, 4),
            "total_interaction_r": round(total_interaction, 4),
            "linear_sum_deltas_r": round(total_delta_p + total_delta_be, 4),
            "interaction_type": "SYNERGISTIC" if total_interaction > 0.05 else ("REDUNDANT_SUBADDITIVE" if total_interaction < -0.05 else "ADDITIVE_INDEPENDENT")
        },
        "runner_convexity_check": {
            "trade_05": next((r for r in matrix_rows if r["index"] == 5), None),
            "trade_10": next((r for r in matrix_rows if r["index"] == 10), None),
        },
        "unmatched_new_trades": unmatched_comp_trades,
        "opportunity_matrix": matrix_rows
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fp:
        json.dump(summary, fp, indent=2)

    print("\n" + "=" * 80)
    print("COMPOSITE INTERACTION ANALYSIS COMPLETE")
    print(f"Executed Counts: Baseline={len(base_trades)} | Polarity={len(pol_trades)} | Breakeven={len(be_trades)} | Composite={len(comp_trades)}")
    print(f"Unmatched/New Trades: {len(unmatched_comp_trades)}")
    print(f"Delta P (Polarity incremental) : {round(total_delta_p, 4)}R")
    print(f"Delta BE (Breakeven incremental): {round(total_delta_be, 4)}R")
    print(f"Delta C (Composite incremental): {round(total_delta_c, 4)}R")
    print(f"Interaction I_total            : {round(total_interaction, 4)}R [{summary['interaction_accounting']['interaction_type']}]")
    print("=" * 80)
    return summary


if __name__ == "__main__":
    run_interaction_analysis()
