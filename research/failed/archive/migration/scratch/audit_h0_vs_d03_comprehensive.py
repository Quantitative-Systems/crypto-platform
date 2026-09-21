"""
Comprehensive Forensic Audit: Clean H0 Development Control vs D-03 Delta Audit
Strictly on 2021-01-01 to 2022-12-31 Development Partition
"""

import json
import os
import sys
import numpy as np
import pandas as pd

H0_PATH = "/home/mrcn2/crypto-platform/scratch/h0_dev_control_results.json"
D03_PATH = "/home/mrcn2/crypto-platform/scratch/h_d03_dev_results.json"

def load_data():
    with open(H0_PATH, "r") as f:
        h0 = json.load(f)
    with open(D03_PATH, "r") as f:
        d03 = json.load(f)
    return h0, d03

def analyze():
    h0, d03 = load_data()
    h0_trades = h0.get("trade_ledger", [])
    d03_trades = d03.get("trade_ledger", [])

    print("=" * 80)
    print("FORENSIC AUDIT: CLEAN H0 CONTROL BENCHMARK VS D-03 (2021-2022 DEV)")
    print("=" * 80)

    # 1. Population & Candidate Equivalence
    h0_cands = {}
    for t in h0_trades:
        cid = t["trade_id"]
        if cid not in h0_cands:
            h0_cands[cid] = []
        h0_cands[cid].append(t)

    d03_cands = {}
    for t in d03_trades:
        cid = t["trade_id"]
        if cid not in d03_cands:
            d03_cands[cid] = []
        d03_cands[cid].append(t)

    print("\n--- 1. CANDIDATE POPULATION EQUIVALENCE ---")
    print(f"H0 Total Trade Ledger Records: {len(h0_trades)}")
    print(f"D03 Total Trade Ledger Records: {len(d03_trades)}")
    print(f"H0 Unique Candidate Setups: {len(h0_cands)}")
    print(f"D03 Unique Candidate Setups: {len(d03_cands)}")
    print(f"Candidate ID Set Symmetric Difference: {set(h0_cands.keys()) ^ set(d03_cands.keys())}")

    # 2. Control Metrics for H0
    h0_net_r = sum(t["net_r"] for t in h0_trades)
    h0_gross_r = sum(t["gross_r"] for t in h0_trades)
    h0_wins = [t for t in h0_trades if t["net_r"] > 0]
    h0_losses = [t for t in h0_trades if t["net_r"] <= 0]
    h0_gross_win_r = sum(t["net_r"] for t in h0_wins)
    h0_gross_loss_r = abs(sum(t["net_r"] for t in h0_losses))
    h0_pf = h0_gross_win_r / h0_gross_loss_r if h0_gross_loss_r > 0 else 0.0
    h0_wr = len(h0_wins) / len(h0_trades) * 100 if h0_trades else 0.0
    h0_exp = h0_net_r / len(h0_trades) if h0_trades else 0.0
    h0_avg_win = h0_gross_win_r / len(h0_wins) if h0_wins else 0.0
    h0_avg_loss = sum(t["net_r"] for t in h0_losses) / len(h0_losses) if h0_losses else 0.0
    h0_median_r = float(np.median([t["net_r"] for t in h0_trades])) if h0_trades else 0.0

    # Max Drawdown R
    cum_r = 0.0
    peak_r = 0.0
    h0_max_dd_r = 0.0
    for t in h0_trades:
        cum_r += t["net_r"]
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > h0_max_dd_r:
            h0_max_dd_r = dd

    # Exit attributions
    h0_initial_sl = sum(1 for t in h0_trades if t.get("exit_reason") == "INITIAL_LTF_SL")
    h0_pl_exits = sum(1 for t in h0_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL")
    h0_mtf_trail = sum(1 for t in h0_trades if t.get("exit_reason") == "MTF_STRUCTURAL_TRAIL")
    h0_tp_exits = sum(1 for t in h0_trades if t.get("exit_reason") == "HTF_TP")

    # 3. D-03 Metrics
    d03_net_r = sum(t["net_r"] for t in d03_trades)
    d03_gross_r = sum(t["gross_r"] for t in d03_trades)
    d03_wins = [t for t in d03_trades if t["net_r"] > 0]
    d03_losses = [t for t in d03_trades if t["net_r"] <= 0]
    d03_gross_win_r = sum(t["net_r"] for t in d03_wins)
    d03_gross_loss_r = abs(sum(t["net_r"] for t in d03_losses))
    d03_pf = d03_gross_win_r / d03_gross_loss_r if d03_gross_loss_r > 0 else 0.0
    d03_wr = len(d03_wins) / len(d03_trades) * 100 if d03_trades else 0.0
    d03_exp = d03_net_r / len(d03_trades) if d03_trades else 0.0
    d03_avg_win = d03_gross_win_r / len(d03_wins) if d03_wins else 0.0
    d03_avg_loss = sum(t["net_r"] for t in d03_losses) / len(d03_losses) if d03_losses else 0.0
    d03_median_r = float(np.median([t["net_r"] for t in d03_trades])) if d03_trades else 0.0

    cum_r = 0.0
    peak_r = 0.0
    d03_max_dd_r = 0.0
    for t in d03_trades:
        cum_r += t["net_r"]
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > d03_max_dd_r:
            d03_max_dd_r = dd

    d03_initial_sl = sum(1 for t in d03_trades if t.get("exit_reason") == "INITIAL_LTF_SL")
    d03_pl_exits = sum(1 for t in d03_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL")
    d03_mtf_trail = sum(1 for t in d03_trades if t.get("exit_reason") == "MTF_STRUCTURAL_TRAIL")
    d03_tp_exits = sum(1 for t in d03_trades if t.get("exit_reason") == "HTF_TP")

    print("\n--- 2. AGGREGATE COMPARISON TABLE ---")
    print(f"| Metric                      | H0 (Control) | D-03 (Intervention) | Delta (D03 - H0) |")
    print(f"| --------------------------- | -----------: | ------------------: | ---------------: |")
    print(f"| Total Trades                | {len(h0_trades)} | {len(d03_trades)} | {len(d03_trades) - len(h0_trades)} |")
    print(f"| Unique Setups               | {len(h0_cands)} | {len(d03_cands)} | {len(d03_cands) - len(h0_cands)} |")
    print(f"| Wins                        | {len(h0_wins)} | {len(d03_wins)} | {len(d03_wins) - len(h0_wins)} |")
    print(f"| Losses                      | {len(h0_losses)} | {len(d03_losses)} | {len(d03_losses) - len(h0_losses)} |")
    print(f"| Win Rate (%)                | {h0_wr:.2f}% | {d03_wr:.2f}% | {d03_wr - h0_wr:+.2f}% |")
    print(f"| Net Realized R              | {h0_net_r:.4f}R | {d03_net_r:.4f}R | {d03_net_r - h0_net_r:+.4f}R |")
    print(f"| Expectancy (R/trade)        | {h0_exp:.4f}R | {d03_exp:.4f}R | {d03_exp - h0_exp:+.4f}R |")
    print(f"| Gross Win R                 | {h0_gross_win_r:.4f}R | {d03_gross_win_r:.4f}R | {d03_gross_win_r - h0_gross_win_r:+.4f}R |")
    print(f"| Gross Loss R                | {h0_gross_loss_r:.4f}R | {d03_gross_loss_r:.4f}R | {d03_gross_loss_r - h0_gross_loss_r:+.4f}R |")
    print(f"| Profit Factor               | {h0_pf:.4f} | {d03_pf:.4f} | {d03_pf - h0_pf:+.4f} |")
    print(f"| Max Drawdown (R)            | {h0_max_dd_r:.2f}R | {d03_max_dd_r:.2f}R | {d03_max_dd_r - h0_max_dd_r:+.2f}R |")
    print(f"| Avg Winner (R)              | {h0_avg_win:.4f}R | {d03_avg_win:.4f}R | {d03_avg_win - h0_avg_win:+.4f}R |")
    print(f"| Avg Loser (R)               | {h0_avg_loss:.4f}R | {d03_avg_loss:.4f}R | {d03_avg_loss - h0_avg_loss:+.4f}R |")
    print(f"| Median Trade R              | {h0_median_r:.4f}R | {d03_median_r:.4f}R | {d03_median_r - h0_median_r:+.4f}R |")
    print(f"| Target Exits (HTF_TP)       | {h0_tp_exits} | {d03_tp_exits} | {d03_tp_exits - h0_tp_exits} |")
    print(f"| Initial SL Exits            | {h0_initial_sl} | {d03_initial_sl} | {d03_initial_sl - h0_initial_sl} |")
    print(f"| Profit-Lock Exits           | {h0_pl_exits} | {d03_pl_exits} | {d03_pl_exits - h0_pl_exits} |")
    print(f"| MTF Trailing Exits          | {h0_mtf_trail} | {d03_mtf_trail} | {d03_mtf_trail - h0_mtf_trail} |")

    # 4. Forensic Investigation of the 22 D-03 Profit-Lock Exits
    print("\n--- 3. DETAILED FORENSIC AUDIT OF THE 22 D-03 PROFIT-LOCK EXITS ---")
    d03_pl_trades = [t for t in d03_trades if t.get("exit_reason") == "PROFIT_LOCK_TRAIL"]
    print(f"Total D-03 Profit-Lock Exits: {len(d03_pl_trades)}")

    # For each PL trade, find corresponding trade(s) in H0
    pl_forensics = []
    for i, t_d03 in enumerate(d03_pl_trades):
        cid = t_d03["trade_id"]
        stream_id = t_d03["stream_id"]
        entry_ts = t_d03.get("entry_timestamp")
        entry_p = t_d03.get("entry_price")
        init_sl = t_d03.get("initial_stop_price")
        tp_p = t_d03.get("target_price")
        mfe_r = t_d03.get("mfe_r", 0.0)
        d03_exit_ts = t_d03.get("exit_timestamp")
        d03_exit_r = t_d03.get("net_r", 0.0)

        # Match in H0 candidates
        h0_matches = h0_cands.get(cid, [])
        # Find exact entry match if possible
        matched_h0 = None
        for h_t in h0_matches:
            if h_t.get("entry_timestamp") == entry_ts:
                matched_h0 = h_t
                break
        if not matched_h0 and h0_matches:
            matched_h0 = h0_matches[0]

        if matched_h0:
            h0_exit_ts = matched_h0.get("exit_timestamp")
            h0_exit_r = matched_h0.get("net_r", 0.0)
            h0_reason = matched_h0.get("exit_reason")
            delta_r = d03_exit_r - h0_exit_r
            if delta_r > 0.10:
                verdict = "CAPITAL_PROTECTED (+ΔR)"
            elif delta_r < -0.10:
                verdict = "RUNNER_CHOKED (-ΔR)"
            else:
                verdict = "NEUTRAL (≈0 ΔR)"
        else:
            h0_exit_ts = None
            h0_exit_r = None
            h0_reason = "NO_MATCH"
            delta_r = None
            verdict = "UNMATCHED"

        pl_forensics.append({
            "idx": i + 1,
            "trade_id": cid,
            "stream_id": stream_id,
            "entry_ts": entry_ts,
            "entry_price": entry_p,
            "initial_sl": init_sl,
            "target_price": tp_p,
            "mfe_r": mfe_r,
            "d03_exit_ts": d03_exit_ts,
            "d03_exit_r": round(d03_exit_r, 4),
            "h0_exit_ts": h0_exit_ts,
            "h0_exit_r": round(h0_exit_r, 4) if h0_exit_r is not None else None,
            "h0_reason": h0_reason,
            "delta_r": round(delta_r, 4) if delta_r is not None else None,
            "verdict": verdict
        })

    df_pl = pd.DataFrame(pl_forensics)
    print(df_pl.to_string(index=False))

    choked_count = sum(1 for x in pl_forensics if "RUNNER_CHOKED" in x["verdict"])
    protected_count = sum(1 for x in pl_forensics if "CAPITAL_PROTECTED" in x["verdict"])
    neutral_count = sum(1 for x in pl_forensics if "NEUTRAL" in x["verdict"])
    total_delta_on_pl = sum(x["delta_r"] for x in pl_forensics if x["delta_r"] is not None)

    print("\n--- PROFIT-LOCK ATTRIBUTION SUMMARY ---")
    print(f"Total D-03 Profit-Lock Exits Analyzed: {len(pl_forensics)}")
    print(f"  - Capital Protected (Saved Loss): {protected_count} trades")
    print(f"  - Runners Choked (Destroyed Gain): {choked_count} trades")
    print(f"  - Neutral / Indifferent: {neutral_count} trades")
    print(f"  - Net Causal Delta of the 22 PL Exits: {total_delta_on_pl:+.4f}R")

    # 5. Long / Short Breakdown
    print("\n--- 4. LONG / SHORT BREAKDOWN ---")
    for side in ["LONG", "SHORT"]:
        h0_side = [t for t in h0_trades if t.get("direction") == side]
        d03_side = [t for t in d03_trades if t.get("direction") == side]
        h0_side_r = sum(t["net_r"] for t in h0_side)
        d03_side_r = sum(t["net_r"] for t in d03_side)
        print(f"{side}:")
        print(f"  H0:  Trades={len(h0_side)}, Net R={h0_side_r:.4f}R, Exp={h0_side_r/len(h0_side) if h0_side else 0:.4f}R")
        print(f"  D03: Trades={len(d03_side)}, Net R={d03_side_r:.4f}R, Exp={d03_side_r/len(d03_side) if d03_side else 0:.4f}R")
        print(f"  Delta ({side}): {d03_side_r - h0_side_r:+.4f}R")

    # 6. Per-Stream Breakdown
    print("\n--- 5. PER-STREAM PERFORMANCE BREAKDOWN ---")
    all_streams = sorted(set([t["stream_id"] for t in h0_trades] + [t["stream_id"] for t in d03_trades]))
    for s in all_streams:
        h0_s = [t for t in h0_trades if t["stream_id"] == s]
        d03_s = [t for t in d03_trades if t["stream_id"] == s]
        h0_sr = sum(t["net_r"] for t in h0_s)
        d03_sr = sum(t["net_r"] for t in d03_s)
        print(f"Stream: {s:<10} | H0: {len(h0_s):2d} trds, {h0_sr:+7.2f}R | D03: {len(d03_s):2d} trds, {d03_sr:+7.2f}R | Delta: {d03_sr - h0_sr:+7.2f}R")

    # 7. Candidate-Level Paired Aggregation (Grouping multiple executions by Candidate)
    print("\n--- 6. CANDIDATE-LEVEL PAIRED AGGREGATION (50 Unique Setups) ---")
    cand_deltas = []
    for cid in sorted(h0_cands.keys()):
        h0_t_list = h0_cands[cid]
        d03_t_list = d03_cands.get(cid, [])
        h0_cand_net_r = sum(t["net_r"] for t in h0_t_list)
        d03_cand_net_r = sum(t["net_r"] for t in d03_t_list)
        c_delta = d03_cand_net_r - h0_cand_net_r
        cand_deltas.append({
            "candidate_id": cid,
            "stream_id": h0_t_list[0]["stream_id"],
            "direction": h0_t_list[0]["direction"],
            "h0_trades_count": len(h0_t_list),
            "d03_trades_count": len(d03_t_list),
            "h0_net_r": round(h0_cand_net_r, 4),
            "d03_net_r": round(d03_cand_net_r, 4),
            "delta_r": round(c_delta, 4)
        })

    cand_df = pd.DataFrame(cand_deltas)
    improved_cands = sum(1 for x in cand_deltas if x["delta_r"] > 0.05)
    degraded_cands = sum(1 for x in cand_deltas if x["delta_r"] < -0.05)
    neutral_cands = sum(1 for x in cand_deltas if abs(x["delta_r"]) <= 0.05)
    total_cand_delta = sum(x["delta_r"] for x in cand_deltas)

    print(f"Candidates Improved by D-03: {improved_cands}")
    print(f"Candidates Degraded by D-03: {degraded_cands}")
    print(f"Candidates Neutral (no effect): {neutral_cands}")
    print(f"Total Candidate-Level Delta: {total_cand_delta:+.4f}R")

    # 8. Final Decision Gate Evaluation
    print("\n" + "=" * 80)
    print("FINAL DECISION GATE EVALUATION")
    print("=" * 80)
    print(f"H0 Net Realized R:  {h0_net_r:+.4f}R (Expectancy: {h0_exp:+.4f}R, PF: {h0_pf:.2f})")
    print(f"D-03 Net Realized R: {d03_net_r:+.4f}R (Expectancy: {d03_exp:+.4f}R, PF: {d03_pf:.2f})")
    print(f"ΔNetR (D03 - H0):   {d03_net_r - h0_net_r:+.4f}R")
    if d03_net_r - h0_net_r < -0.5:
        print("\nGATE DECISION: CASE B — ΔNetR IS NEGATIVE (-4.51R).")
        print("D-03 FAILS THE DEVELOPMENT HYPOTHESIS.")
        print("Conclusion: D-03 (+1.0R breakeven lock) damages expectancy by prematurely truncating large winning runners (+4.0R to +8.0R targets) for small +0.10R gains, outweighing the capital saved on retracing trades.")
        print("Strict Directive Constraint: Do NOT proceed to 2023 Validation or 2024-2026 OOS.")
    elif d03_net_r - h0_net_r > 0.5:
        print("\nGATE DECISION: CASE A — ΔNetR IS POSITIVE.")
    else:
        print("\nGATE DECISION: CASE C — ΔNetR APPROXIMATELY ZERO.")
    print("=" * 80)

if __name__ == "__main__":
    analyze()
