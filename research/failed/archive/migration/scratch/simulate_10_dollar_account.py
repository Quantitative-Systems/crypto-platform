import os
import json
import glob
from datetime import datetime

# Load all individual stream result JSONs in research/results
files = glob.glob("/home/mrcn2/crypto-platform/research/results/BASELINE_001_*.json")

# Also let's check canonical results
with open("/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json", "r") as f:
    streams = json.load(f)

# Portfolio metrics over total duration (~4 years)
total_trades = sum(s["total_trades"] for s in streams)
total_r = sum(s["total_realized_r"] for s in streams)
win_rate = sum(s["wins"] for s in streams) / total_trades
avg_r = total_r / total_trades

# Annualized figures
years = 4.0
trades_per_year = total_trades / years
annual_realized_r = total_r / years

print(f"Total Trades (4 years): {total_trades}")
print(f"Trades per Year: {trades_per_year:.1f}")
print(f"Annual Realized R: +{annual_realized_r:.2f}R")
print(f"Expectancy per trade: +{avg_r:.2f}R")

# Simulation A: Pure Fractional Compounding at 1% Risk ($10 Initial)
# Trade by trade compounding: Equity_t = Equity_{t-1} * (1 + risk_pct * R_t)
# Over N trades in 1 year with mean = avg_r, win_rate = 53.2%, avg_win = +1.74R (Hyp B) / +1.0R (Hyp A), avg_loss = -1.0R
def simulate_compounding(initial_balance=10.0, risk_pct=0.01, annual_trades=347, exp_r=0.53):
    # Log-growth geometric mean approximation
    # E[ln(1 + f * R)]
    eq = initial_balance
    for _ in range(int(annual_trades)):
        eq *= (1.0 + risk_pct * exp_r)
    return eq

def simulate_monte_carlo(initial_balance=10.0, risk_pct=0.01, annual_trades=347, n_sims=1000):
    import numpy as np
    # 53.2% win rate, win = +1.87R, loss = -1.03R
    final_balances = []
    for _ in range(n_sims):
        eq = initial_balance
        for _ in range(annual_trades):
            is_win = np.random.rand() < 0.532
            r = np.random.uniform(1.2, 2.5) if is_win else np.random.uniform(-1.05, -1.00)
            pnl = eq * risk_pct * r
            eq += pnl
            if eq <= 0:
                eq = 0
                break
        final_balances.append(eq)
    return np.percentile(final_balances, [10, 50, 90])

p10, p50, p90 = simulate_monte_carlo(10.0, 0.01, int(trades_per_year))
p10_2, p50_2, p90_2 = simulate_monte_carlo(10.0, 0.02, int(trades_per_year))

print("\n--- MONTE CARLO 1-YEAR RESULTS ON $10 ACCOUNT ---")
print(f"1% Risk per trade: Median Ending Balance = ${p50:.2f} (10th-90th percentile: ${p10:.2f} - ${p90:.2f})")
print(f"2% Risk per trade: Median Ending Balance = ${p50_2:.2f} (10th-90th percentile: ${p10_2:.2f} - ${p90_2:.2f})")
