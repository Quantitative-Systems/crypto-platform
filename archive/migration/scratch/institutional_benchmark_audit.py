import json
import numpy as np

with open("/home/mrcn2/crypto-platform/scratch/gate5b_24_stream_forensic_results.json", "r") as f:
    forensic = json.load(f)

with open("/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json", "r") as f:
    canon = json.load(f)

# Control baseline streams (all trades)
control = forensic["control_baseline_24_streams"]
hyp_b_trades_count = sum(s["strategy_b"]["metrics"]["total_trades"] for s in control)
hyp_b_wins = sum(s["strategy_b"]["metrics"]["wins"] for s in control)
hyp_b_gp = sum(s["strategy_b"]["metrics"]["gross_profit"] for s in control)
hyp_b_gl = sum(s["strategy_b"]["metrics"]["gross_loss"] for s in control)
hyp_b_pnl = sum(s["strategy_b"]["metrics"]["net_pnl"] for s in control)
hyp_b_r = sum(s["strategy_b"]["metrics"]["total_realized_r"] for s in control)

# Calculate annual metrics
years = 4.0
annual_trades_b = hyp_b_trades_count / years
annual_r_b = hyp_b_r / years
annual_pnl_b = hyp_b_pnl / years
pf_b = hyp_b_gp / hyp_b_gl
wr_b = (hyp_b_wins / hyp_b_trades_count) * 100.0
exp_b = hyp_b_r / hyp_b_trades_count

# Combined matrix
tot_trades = sum(s["total_trades"] for s in canon)
tot_wins = sum(s["wins"] for s in canon)
tot_gp = sum(s["gross_profit"] for s in canon)
tot_gl = sum(s["gross_loss"] for s in canon)
tot_pnl = sum(s["net_pnl"] for s in canon)
tot_r = sum(s["total_realized_r"] for s in canon)

pf_comb = tot_gp / tot_gl
wr_comb = (tot_wins / tot_trades) * 100.0
exp_comb = tot_r / tot_trades

print(f"HYPOTHESIS B (ELITE CONTINUATION):")
print(f"  • Trades: {hyp_b_trades_count} ({annual_trades_b:.1f}/yr)")
print(f"  • Win Rate: {wr_b:.1f}%")
print(f"  • Profit Factor: {pf_b:.2f}")
print(f"  • Net Realized R: +{hyp_b_r:.1f}R (+{annual_r_b:.1f}R/yr)")
print(f"  • Net PnL ($10k base): ${hyp_b_pnl:+,.2f} (${annual_pnl_b:+,.2f}/yr)")
print(f"  • Expectancy: +{exp_b:.2f}R / trade")

print(f"\nFULL PORTFOLIO (HYP A + B):")
print(f"  • Trades: {tot_trades}")
print(f"  • Win Rate: {wr_comb:.1f}%")
print(f"  • Profit Factor: {pf_comb:.2f}")
print(f"  • Net Realized R: +{tot_r:.1f}R")
print(f"  • Net PnL ($10k base): ${tot_pnl:+,.2f}")
print(f"  • Expectancy: +{exp_comb:.2f}R / trade")
