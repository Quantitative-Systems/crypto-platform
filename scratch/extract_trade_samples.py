"""
Extract trade samples for Requirement 3.
"""

import pandas as pd

df = pd.read_csv('/home/mrcn2/automated_trading_os/trades.csv')

def print_trade_table(title, subset):
    print("\n" + "=" * 120)
    print(f"SAMPLE: {title} ({len(subset)} trades)")
    print("=" * 120)
    print(f"{'Idx':<4} | {'Symbol':<8} | {'Set':<18} | {'Strategy':<22} | {'Side':<4} | {'Entry':<10} | {'SL':<10} | {'TP':<10} | {'Exit':<10} | {'Reason':<16} | {'R-Mult':<7} | {'PnL ($)':<8}")
    print("-" * 120)
    for idx, row in subset.iterrows():
        print(f"{idx:<4} | {row['symbol']:<8} | {row['set_id']:<18} | {row['strategy']:<22} | {row['action']:<4} | {row['entry_price']:<10.2f} | {row['stop_loss']:<10.2f} | {row['take_profit']:<10.2f} | {row['exit_price']:<10.2f} | {row['exit_reason']:<16} | {row['r_multiple']:>+6.2f}R | {row['pnl']:>+8.2f}")

# First 20
print_trade_table("FIRST 20 TRADES", df.head(20))

# Last 20
print_trade_table("LAST 20 TRADES", df.tail(20))

# 20 Winners
winners = df[df['pnl'] > 0].head(20)
print_trade_table("20 WINNING TRADES (SAMPLE)", winners)

# 20 Losers
losers = df[df['pnl'] <= 0].head(20)
print_trade_table("20 LOSING TRADES (SAMPLE)", losers)
