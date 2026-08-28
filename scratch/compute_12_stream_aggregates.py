"""
Compute aggregate summary across the 12-stream matrix results.
"""

import json

with open("/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json", "r") as f:
    streams = json.load(f)

print("=" * 110)
print(f"{'Stream':<35} | {'Trades':<6} | {'WR (%)':<7} | {'PF':<6} | {'Net PnL ($)':<12} | {'Total R':<9} | {'Avg R':<7} | {'Max DD':<7}")
print("=" * 110)

total_trades = 0
total_wins = 0
total_losses = 0
total_gp = 0.0
total_gl = 0.0
total_net_pnl = 0.0
total_realized_r = 0.0

for s in streams:
    total_trades += s["total_trades"]
    total_wins += s["wins"]
    total_losses += s["losses"]
    total_gp += s["gross_profit"]
    total_gl += s["gross_loss"]
    total_net_pnl += s["net_pnl"]
    total_realized_r += s["total_realized_r"]
    
    label = f"{s['symbol']} | {s['tf_set_id']}"
    print(f"{label:<35} | {s['total_trades']:<6} | {s['win_rate_pct']:<7.2f} | {s['profit_factor']:<6.2f} | ${s['net_pnl']:<11,.2f} | {s['total_realized_r']:<+8.2f}R | {s['avg_realized_r']:<+6.2f}R | {s['max_drawdown_pct']:<6.2f}%")

print("-" * 110)
agg_wr = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
agg_pf = (total_gp / total_gl) if total_gl > 0 else 0.0
agg_avg_r = (total_realized_r / total_trades) if total_trades > 0 else 0.0

print(f"{'TOTAL 12-STREAM PORTFOLIO':<35} | {total_trades:<6} | {agg_wr:<7.2f} | {agg_pf:<6.2f} | ${total_net_pnl:<11,.2f} | {total_realized_r:<+8.2f}R | {agg_avg_r:<+6.2f}R |")
print("=" * 110)

print("\n--- AGGREGATION BY TIMEFRAME SET ---")
for tf_set_id in ["SET_1", "SET_2", "SET_3", "SET_4"]:
    subset = [s for s in streams if s["tf_set_id"] == tf_set_id]
    t = sum(s["total_trades"] for s in subset)
    w = sum(s["wins"] for s in subset)
    gp = sum(s["gross_profit"] for s in subset)
    gl = sum(s["gross_loss"] for s in subset)
    pnl = sum(s["net_pnl"] for s in subset)
    tot_r = sum(s["total_realized_r"] for s in subset)
    wr = (w / t * 100.0) if t > 0 else 0.0
    pf = (gp / gl) if gl > 0 else 0.0
    avg_r = (tot_r / t) if t > 0 else 0.0
    print(f"  {tf_set_id:<8} | Trades: {t:4d} | WR: {wr:5.2f}% | PF: {pf:5.2f} | Net PnL: ${pnl:+12,.2f} | Total R: {tot_r:+8.2f}R | Avg R: {avg_r:+5.2f}R")

print("\n--- AGGREGATION BY ASSET ---")
for asset in ["BTC", "ETH", "SOL"]:
    subset = [s for s in streams if s["symbol"].startswith(asset)]
    t = sum(s["total_trades"] for s in subset)
    w = sum(s["wins"] for s in subset)
    gp = sum(s["gross_profit"] for s in subset)
    gl = sum(s["gross_loss"] for s in subset)
    pnl = sum(s["net_pnl"] for s in subset)
    tot_r = sum(s["total_realized_r"] for s in subset)
    wr = (w / t * 100.0) if t > 0 else 0.0
    pf = (gp / gl) if gl > 0 else 0.0
    avg_r = (tot_r / t) if t > 0 else 0.0
    print(f"  {asset:<8} | Trades: {t:4d} | WR: {wr:5.2f}% | PF: {pf:5.2f} | Net PnL: ${pnl:+12,.2f} | Total R: {tot_r:+8.2f}R | Avg R: {avg_r:+5.2f}R")
