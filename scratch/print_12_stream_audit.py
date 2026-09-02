import json

with open("/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json", "r") as f:
    streams = json.load(f)

print("=" * 125)
print("CANONICAL 12-STREAM MATRIX AUDIT REPORT")
print("=" * 125)
print(f"{'Stream':<30} | {'Trades':<6} | {'WR %':<7} | {'PF':<6} | {'Net PnL ($)':<12} | {'Total R':<10} | {'Avg R':<8} | {'Max DD%':<8} | {'Max Loss Streak':<15}")
print("-" * 125)

tot_trades = 0
tot_wins = 0
tot_pnl = 0.0
tot_r = 0.0

for s in streams:
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
    max_streak = s.get("max_consecutive_losses", 0)

    tot_trades += t
    tot_wins += w
    tot_pnl += pnl
    tot_r += r

    print(f"{sym+' '+set_id:<30} | {t:<6} | {wr:<6.1f}% | {pf:<6.2f} | ${pnl:<11,.2f} | {r:<+9.2f}R | {avg_r:<+7.2f}R | {mdd:<7.1f}% | {max_streak:<15}")

print("=" * 125)
print(f"PORTFOLIO TOTAL: Trades: {tot_trades} | Wins: {tot_wins} (WR: {tot_wins/tot_trades*100:.1f}%) | Net PnL: ${tot_pnl:,.2f} | Total Realized R: {tot_r:+.2f}R | Avg Expectancy: {tot_r/tot_trades:+.2f}R")
