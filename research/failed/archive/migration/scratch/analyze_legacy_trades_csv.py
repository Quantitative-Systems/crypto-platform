"""
Detailed forensic analysis script for /home/mrcn2/automated_trading_os/trades.csv.
"""

import pandas as pd
import numpy as np

csv_path = '/home/mrcn2/automated_trading_os/trades.csv'
df = pd.read_csv(csv_path)

print(f"Total Rows: {len(df)}")
print("\n--- SCHEMA ---")
for col, dtype in df.dtypes.items():
    print(f"  {col}: {dtype}")

print("\n" + "=" * 90)
print("1. COMPLETE BREAKDOWN BY SYMBOL + SET_ID")
print("=" * 90)

grouped = df.groupby(['symbol', 'set_id'])

summary_rows = []

for (sym, set_id), group in grouped:
    t_count = len(group)
    wins = group[group['pnl'] > 0]
    losses = group[group['pnl'] <= 0]
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / t_count) * 100.0 if t_count > 0 else 0.0
    
    gp = wins['pnl'].sum() if w_count > 0 else 0.0
    gl = abs(losses['pnl'].sum()) if l_count > 0 else 0.0
    pf = (gp / gl) if gl > 0 else (gp if gp > 0 else 0.0)
    net_pnl = group['pnl'].sum()
    
    r_vals = group['r_multiple'].to_numpy()
    avg_r = np.mean(r_vals) if t_count > 0 else 0.0
    med_r = np.median(r_vals) if t_count > 0 else 0.0
    
    avg_win_r = wins['r_multiple'].mean() if w_count > 0 else 0.0
    avg_loss_r = losses['r_multiple'].mean() if l_count > 0 else 0.0
    
    # Cumulative equity & Max DD
    cum_pnl = group['pnl'].cumsum()
    peak = cum_pnl.cummax()
    dd = peak - cum_pnl
    max_dd_usd = dd.max() if len(dd) > 0 else 0.0
    
    # Max consecutive losses
    curr_losses = 0
    max_losses = 0
    for pnl in group['pnl']:
        if pnl <= 0:
            curr_losses += 1
            if curr_losses > max_losses:
                max_losses = curr_losses
        else:
            curr_losses = 0
            
    # Exit reasons
    exit_dist = group['exit_reason'].value_counts().to_dict()
    
    summary_rows.append({
        'symbol': sym,
        'set_id': set_id,
        'trades': t_count,
        'wins': w_count,
        'losses': l_count,
        'win_rate': wr,
        'gross_profit': gp,
        'gross_loss': gl,
        'profit_factor': pf,
        'net_pnl': net_pnl,
        'avg_r': avg_r,
        'median_r': med_r,
        'avg_win_r': avg_win_r,
        'avg_loss_r': avg_loss_r,
        'max_dd_usd': max_dd_usd,
        'max_consecutive_losses': max_losses,
        'exit_reasons': exit_dist
    })

for r in summary_rows:
    print(f"\n[{r['symbol']} | {r['set_id']}]")
    print(f"  Trades: {r['trades']} | Wins: {r['wins']} | Losses: {r['losses']} | Win Rate: {r['win_rate']:.2f}%")
    print(f"  Gross Profit: ${r['gross_profit']:.2f} | Gross Loss: ${r['gross_loss']:.2f} | Profit Factor: {r['profit_factor']:.2f} | Net PnL: ${r['net_pnl']:.2f}")
    print(f"  Avg R: {r['avg_r']:+.2f}R | Median R: {r['median_r']:+.2f}R | Avg Win: {r['avg_win_r']:+.2f}R | Avg Loss: {r['avg_loss_r']:+.2f}R")
    print(f"  Max DD: ${r['max_dd_usd']:.2f} | Max Cons Losses: {r['max_consecutive_losses']}")
    print(f"  Exit Reasons: {r['exit_reasons']}")

print("\n" + "=" * 90)
print("2. AGGREGATED SUMMARY BY SET_ID")
print("=" * 90)
for set_id, group in df.groupby('set_id'):
    t_count = len(group)
    wins = group[group['pnl'] > 0]
    losses = group[group['pnl'] <= 0]
    wr = (len(wins) / t_count) * 100.0
    gp = wins['pnl'].sum()
    gl = abs(losses['pnl'].sum())
    pf = (gp / gl) if gl > 0 else gp
    print(f"  {set_id:<22} | Trades: {t_count:3d} | WR: {wr:5.1f}% | PF: {pf:5.2f} | Net: ${group['pnl'].sum():+7.2f} | Avg R: {group['r_multiple'].mean():+5.2f}R | Exits: {group['exit_reason'].value_counts().to_dict()}")

print("\n" + "=" * 90)
print("3. AGGREGATED SUMMARY BY SYMBOL")
print("=" * 90)
for sym, group in df.groupby('symbol'):
    t_count = len(group)
    wins = group[group['pnl'] > 0]
    losses = group[group['pnl'] <= 0]
    wr = (len(wins) / t_count) * 100.0
    gp = wins['pnl'].sum()
    gl = abs(losses['pnl'].sum())
    pf = (gp / gl) if gl > 0 else gp
    print(f"  {sym:<10} | Trades: {t_count:3d} | WR: {wr:5.1f}% | PF: {pf:5.2f} | Net: ${group['pnl'].sum():+7.2f} | Avg R: {group['r_multiple'].mean():+5.2f}R | Exits: {group['exit_reason'].value_counts().to_dict()}")
