"""
Parse and display the complete Gate 5B 24-Stream Forensic Matrix and Ablation Report.
"""

import json

with open("/home/mrcn2/crypto-platform/scratch/gate5b_24_stream_forensic_results.json", "r") as f:
    bundle = json.load(f)

control = bundle["control_baseline_24_streams"]
ablation_no_pl = bundle["ablation_no_profit_lock"]
ablation_no_mtf = bundle["ablation_no_mtf_trailing"]

TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4"]
TF_SET_LABELS = {
    "SET_1": "SET_1_INVESTING (1M -> 1W -> 1D)",
    "SET_2": "SET_2_POSITIONAL (1W -> 1D -> 4H)",
    "SET_3": "SET_3_SWING (1D -> 4H -> 1H)",
    "SET_4": "SET_4_INTRADAY (4H -> 1H -> 15M)"
}

print("=" * 130)
print("PROJECT TOP1 — GATE 5B: FULL 24-STREAM FORENSIC MATRIX REPORT")
print("=" * 130)

print("\n" + "=" * 130)
print("SECTION 1 & 4: THE 24-STREAM FORENSIC PERFORMANCE MATRIX")
print("=" * 130)
header = f"{'Stream (Asset / Set / Strategy)':<38} | {'Trd':<4} | {'WR%':<5} | {'PF':<5} | {'E[R]':<6} | {'Net R':<8} | {'Net PnL ($)':<11} | {'AvgW/L (R)':<13} | {'MedR':<5} | {'MaxDD%':<6} | {'Strk(W/L)':<9} | {'Dur(h)':<6} | {'MFE/MAE(R)':<12} | {'MFE Conv':<8} | {'Status':<16}"
print(header)
print("-" * 180)

for s in control:
    sym = s["symbol"]
    set_id = s["tf_set_id"]
    
    # Hyp A (Pullback)
    a = s["strategy_a"]
    am = a["metrics"]
    a_label = f"{sym} | {set_id} | Pullback (A)"
    a_wl = f"{am['avg_win_r']:+.1f}/{am['avg_loss_r']:+.1f}"
    a_strk = f"{am['longest_win_streak']}/{am['longest_loss_streak']}"
    a_mfemae = f"{am['avg_mfe_r']:.1f}/{am['avg_mae_r']:.1f}"
    print(f"{a_label:<38} | {am['total_trades']:<4} | {am['win_rate_pct']:<5.1f} | {am['profit_factor']:<5.2f} | {am['expectancy_r']:<+6.2f} | {am['total_realized_r']:<+8.1f} | ${am['net_pnl']:<10,.0f} | {a_wl:<13} | {am['median_r']:<+5.2f} | {am['max_drawdown_pct']:<5.1f}% | {a_strk:<9} | {am['avg_duration_hours']:<6.1f} | {a_mfemae:<12} | {am['mfe_to_realized_conversion']:<8.2f} | {a['status']:<16}")
    
    # Hyp B (Continuation)
    b = s["strategy_b"]
    bm = b["metrics"]
    b_label = f"{sym} | {set_id} | Contin (B)"
    b_wl = f"{bm['avg_win_r']:+.1f}/{bm['avg_loss_r']:+.1f}"
    b_strk = f"{bm['longest_win_streak']}/{bm['longest_loss_streak']}"
    b_mfemae = f"{bm['avg_mfe_r']:.1f}/{bm['avg_mae_r']:.1f}"
    print(f"{b_label:<38} | {bm['total_trades']:<4} | {bm['win_rate_pct']:<5.1f} | {bm['profit_factor']:<5.2f} | {bm['expectancy_r']:<+6.2f} | {bm['total_realized_r']:<+8.1f} | ${bm['net_pnl']:<10,.0f} | {b_wl:<13} | {bm['median_r']:<+5.2f} | {bm['max_drawdown_pct']:<5.1f}% | {b_strk:<9} | {bm['avg_duration_hours']:<6.1f} | {b_mfemae:<12} | {bm['mfe_to_realized_conversion']:<8.2f} | {b['status']:<16}")

print("-" * 180)

# Section 5: Exit Attribution
print("\n" + "=" * 130)
print("SECTION 5: EXIT ATTRIBUTION BY STREAM (COUNT, %, AVG REALIZED R)")
print("=" * 130)
for s in control:
    sym = s["symbol"]
    set_id = s["tf_set_id"]
    cm = s["combined"]["metrics"]
    print(f"\n[{sym} | {set_id}] (Total Trades: {cm['total_trades']})")
    for exit_k, count in cm["exit_attribution"].items():
        pct = cm["exit_percentages"].get(exit_k, 0.0)
        avg_r = cm["exit_avg_r"].get(exit_k, 0.0)
        print(f"  - {exit_k:<24}: {count:3d} ({pct:5.1f}%) | Avg Realized R: {avg_r:+6.2f}R")

# Section 6: Strategy A vs Strategy B
print("\n" + "=" * 130)
print("SECTION 6: STRATEGY A (PULLBACK) VS STRATEGY B (CONTINUATION) AGGREGATE DECOMPOSITION")
print("=" * 130)

tot_a_trades = sum(s["strategy_a"]["metrics"]["total_trades"] for s in control)
tot_a_wins = sum(s["strategy_a"]["metrics"]["wins"] for s in control)
tot_a_gp = sum(s["strategy_a"]["metrics"]["gross_profit"] for s in control)
tot_a_gl = sum(s["strategy_a"]["metrics"]["gross_loss"] for s in control)
tot_a_pnl = sum(s["strategy_a"]["metrics"]["net_pnl"] for s in control)
tot_a_r = sum(s["strategy_a"]["metrics"]["total_realized_r"] for s in control)

tot_b_trades = sum(s["strategy_b"]["metrics"]["total_trades"] for s in control)
tot_b_wins = sum(s["strategy_b"]["metrics"]["wins"] for s in control)
tot_b_gp = sum(s["strategy_b"]["metrics"]["gross_profit"] for s in control)
tot_b_gl = sum(s["strategy_b"]["metrics"]["gross_loss"] for s in control)
tot_b_pnl = sum(s["strategy_b"]["metrics"]["net_pnl"] for s in control)
tot_b_r = sum(s["strategy_b"]["metrics"]["total_realized_r"] for s in control)

print(f"Strategy A (Pullback Riding):     Trades: {tot_a_trades:4d} | WR: {tot_a_wins/tot_a_trades*100:5.2f}% | PF: {tot_a_gp/tot_a_gl:5.2f} | Net PnL: ${tot_a_pnl:+12,.2f} | Total Realized R: {tot_a_r:+8.2f}R | Avg R: {tot_a_r/tot_a_trades:+5.2f}R")
print(f"Strategy B (Continuation Riding): Trades: {tot_b_trades:4d} | WR: {tot_b_wins/tot_b_trades*100:5.2f}% | PF: {tot_b_gp/tot_b_gl:5.2f} | Net PnL: ${tot_b_pnl:+12,.2f} | Total Realized R: {tot_b_r:+8.2f}R | Avg R: {tot_b_r/tot_b_trades:+5.2f}R")

# Section 7: Set Comparison
print("\n" + "=" * 130)
print("SECTION 7: TIMEFRAME SET HORIZON COMPARISON")
print("=" * 130)
for tf_set_id in TF_SETS:
    subset = [s for s in control if s["tf_set_id"] == tf_set_id]
    t = sum(s["combined"]["metrics"]["total_trades"] for s in subset)
    w = sum(s["combined"]["metrics"]["wins"] for s in subset)
    gp = sum(s["combined"]["metrics"]["gross_profit"] for s in subset)
    gl = sum(s["combined"]["metrics"]["gross_loss"] for s in subset)
    pnl = sum(s["combined"]["metrics"]["net_pnl"] for s in subset)
    tot_r = sum(s["combined"]["metrics"]["total_realized_r"] for s in subset)
    wr = (w / t * 100.0) if t > 0 else 0.0
    pf = (gp / gl) if gl > 0 else 0.0
    avg_r = (tot_r / t) if t > 0 else 0.0
    print(f"  {TF_SET_LABELS[tf_set_id]:<38} | Trades: {t:4d} | WR: {wr:5.2f}% | PF: {pf:5.2f} | Net PnL: ${pnl:+12,.2f} | Total R: {tot_r:+8.2f}R | Avg R: {avg_r:+5.2f}R")

# Section 8: Ablation Study
print("\n" + "=" * 130)
print("SECTION 8: CONTROLLED ABLATION STUDY COMPARISON")
print("=" * 130)
print(f"{'Configuration':<35} | {'Trades':<6} | {'WR (%)':<7} | {'PF':<6} | {'Net PnL ($)':<14} | {'Total Realized R':<18} | {'Expectancy E[R]':<15}")
print("-" * 110)

def summarize_run(run_matrix, label):
    t = sum(s["combined"]["metrics"]["total_trades"] for s in run_matrix)
    w = sum(s["combined"]["metrics"]["wins"] for s in run_matrix)
    gp = sum(s["combined"]["metrics"]["gross_profit"] for s in run_matrix)
    gl = sum(s["combined"]["metrics"]["gross_loss"] for s in run_matrix)
    pnl = sum(s["combined"]["metrics"]["net_pnl"] for s in run_matrix)
    tot_r = sum(s["combined"]["metrics"]["total_realized_r"] for s in run_matrix)
    wr = (w / t * 100.0) if t > 0 else 0.0
    pf = (gp / gl) if gl > 0 else 0.0
    exp_r = (tot_r / t) if t > 0 else 0.0
    print(f"{label:<35} | {t:<6} | {wr:<7.2f} | {pf:<6.2f} | ${pnl:<13,.2f} | {tot_r:<+17.2f}R | {exp_r:<+14.2f}R")

summarize_run(control, "CONTROL (Full Canonical)")
summarize_run(ablation_no_pl, "ABLATION A (No Profit-Lock)")
summarize_run(ablation_no_mtf, "ABLATION B (No MTF Trailing)")
