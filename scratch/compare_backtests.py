import json

with open("/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json", "r") as f:
    canon = json.load(f)

with open("/home/mrcn2/crypto-platform/research/results/INSTITUTIONAL_12_STREAM_MATRIX.json", "r") as f:
    inst = json.load(f)

with open("/home/mrcn2/crypto-platform/scratch/gate5b_24_stream_forensic_results.json", "r") as f:
    forensic = json.load(f)

print("=" * 140)
print("                                INSTITUTIONAL BACKTEST REPORT: ALL 4 SETS x ALL 3 ASSETS")
print("=" * 140)

print(f"{'Stream (Asset / Timeframe)':<32} | {'Trades':<6} | {'Win %':<6} | {'PF':<6} | {'Net Realized R':<14} | {'Net PnL ($)':<13} | {'Avg R/Trade':<11} | {'Max DD%':<8}")
print("-" * 140)

tot_trades = 0
tot_wins = 0
tot_pnl = 0.0
tot_r = 0.0
tot_gp = 0.0
tot_gl = 0.0

for s in canon:
    sym = s["symbol"]
    set_id = s["tf_set_id"]
    t = s["total_trades"]
    w = s["wins"]
    wr = s["win_rate_pct"]
    pf = s["profit_factor"]
    pnl = s["net_pnl"]
    r = s["total_realized_r"]
    avg_r = s["avg_realized_r"]
    mdd = s["max_drawdown_pct"]

    tot_trades += t
    tot_wins += w
    tot_pnl += pnl
    tot_r += r
    tot_gp += s["gross_profit"]
    tot_gl += s["gross_loss"]

    label = f"{sym} | {s['tf_set_label'].split(' ')[0]}"
    print(f"{label:<32} | {t:<6} | {wr:<5.1f}% | {pf:<6.2f} | {r:<+13.2f}R | ${pnl:<12,.2f} | {avg_r:<+10.2f}R | {mdd:<7.1f}%")

print("-" * 140)
overall_wr = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
overall_pf = (tot_gp / tot_gl) if tot_gl > 0 else 0.0
overall_exp = (tot_r / tot_trades) if tot_trades > 0 else 0.0
print(f"{'PORTFOLIO AGGREGATE TOTAL':<32} | {tot_trades:<6} | {overall_wr:<5.1f}% | {overall_pf:<6.2f} | {tot_r:<+13.2f}R | ${tot_pnl:<12,.2f} | {overall_exp:<+10.2f}R | -")
print("=" * 140)

# Strategy A vs Strategy B from Gate 5B Forensic
control = forensic["control_baseline_24_streams"]
tot_a_t = sum(s["strategy_a"]["metrics"]["total_trades"] for s in control)
tot_a_w = sum(s["strategy_a"]["metrics"]["wins"] for s in control)
tot_a_gp = sum(s["strategy_a"]["metrics"]["gross_profit"] for s in control)
tot_a_gl = sum(s["strategy_a"]["metrics"]["gross_loss"] for s in control)
tot_a_pnl = sum(s["strategy_a"]["metrics"]["net_pnl"] for s in control)
tot_a_r = sum(s["strategy_a"]["metrics"]["total_realized_r"] for s in control)

tot_b_t = sum(s["strategy_b"]["metrics"]["total_trades"] for s in control)
tot_b_w = sum(s["strategy_b"]["metrics"]["wins"] for s in control)
tot_b_gp = sum(s["strategy_b"]["metrics"]["gross_profit"] for s in control)
tot_b_gl = sum(s["strategy_b"]["metrics"]["gross_loss"] for s in control)
tot_b_pnl = sum(s["strategy_b"]["metrics"]["net_pnl"] for s in control)
tot_b_r = sum(s["strategy_b"]["metrics"]["total_realized_r"] for s in control)

print("\n" + "=" * 140)
print("                                ALPHA MODULE DECOMPOSITION (HYPOTHESIS A vs HYPOTHESIS B)")
print("=" * 140)
print(f"{'Strategy Hypothesis':<35} | {'Trades':<6} | {'Win %':<6} | {'PF':<6} | {'Net Realized R':<14} | {'Net PnL ($)':<13} | {'Avg R/Trade':<11}")
print("-" * 140)
print(f"{'Hypothesis B (Continuation Riding)':<35} | {tot_b_t:<6} | {tot_b_w/tot_b_t*100:<5.1f}% | {tot_b_gp/tot_b_gl:<6.2f} | {tot_b_r:<+13.2f}R | ${tot_b_pnl:<12,.2f} | {tot_b_r/tot_b_t:<+10.2f}R")
print(f"{'Hypothesis A (Pullback Riding)':<35} | {tot_a_t:<6} | {tot_a_w/tot_a_t*100:<5.1f}% | {tot_a_gp/tot_a_gl:<6.2f} | {tot_a_r:<+13.2f}R | ${tot_a_pnl:<12,.2f} | {tot_a_r/tot_a_t:<+10.2f}R")
print("=" * 140)

# Timeframe breakdown
print("\n" + "=" * 140)
print("                                          TIMEFRAME HORIZON BREAKDOWN")
print("=" * 140)
for tf_set_id in ["SET_1", "SET_2", "SET_3", "SET_4"]:
    sub = [s for s in canon if s["tf_set_id"] == tf_set_id]
    t = sum(x["total_trades"] for x in sub)
    w = sum(x["wins"] for x in sub)
    gp = sum(x["gross_profit"] for x in sub)
    gl = sum(x["gross_loss"] for x in sub)
    pnl = sum(x["net_pnl"] for x in sub)
    r = sum(x["total_realized_r"] for x in sub)
    wr = (w / t * 100.0) if t > 0 else 0.0
    pf = (gp / gl) if gl > 0 else 0.0
    exp_r = (r / t) if t > 0 else 0.0
    label = sub[0]["tf_set_label"]
    print(f"  • {label:<38} | Trades: {t:4d} | WR: {wr:5.1f}% | PF: {pf:5.2f} | Net PnL: ${pnl:+12,.2f} | Realized R: {r:+8.1f}R | Exp E[R]: {exp_r:+5.2f}R")
print("=" * 140)
