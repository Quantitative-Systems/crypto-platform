import json
import numpy as np

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
    pl = json.load(f)

h0_trades = h0['all_trades']
pl_trades = pl['all_trades']

def compute_detailed_stats(trades):
    n = len(trades)
    r_vals = [t['realized_rr'] for t in trades]
    gross_vals = [t.get('gross_r', t['realized_rr'] + t.get('fees_r', 0) + t.get('slippage_r', 0)) for t in trades]
    friction_vals = [t.get('fees_r', 0) + t.get('slippage_r', 0) for t in trades]
    wins = [r for r in r_vals if r > 0.0001]
    losses = [r for r in r_vals if r < -0.0001]
    bes = [r for r in r_vals if abs(r) <= 0.0001]

    win_rate = (len(wins) / n * 100) if n > 0 else 0.0
    gross_r = sum(gross_vals)
    net_r = sum(r_vals)
    friction_r = sum(friction_vals)
    expectancy = net_r / n if n > 0 else 0.0

    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)

    # Max Drawdown
    cum_equity = np.cumsum([0.0] + r_vals)
    peak = np.maximum.accumulate(cum_equity)
    dd = peak - cum_equity
    max_dd = float(np.max(dd))

    # Consec losses
    max_consec = 0
    curr_consec = 0
    for r in r_vals:
        if r < 0:
            curr_consec += 1
            max_consec = max(max_consec, curr_consec)
        else:
            curr_consec = 0

    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    median_win = float(np.median(wins)) if wins else 0.0
    median_loss = float(np.median(losses)) if losses else 0.0

    mfe_vals = [t.get('mfe_r', (t['metadata'].get('mfe_price', t['entry_price']) - t['entry_price']) / abs(t['entry_price'] - t['initial_stop_price'])) for t in trades]
    mae_vals = [t.get('mae_r', (t['entry_price'] - t['metadata'].get('mae_price', t['entry_price'])) / abs(t['entry_price'] - t['initial_stop_price'])) for t in trades]

    exit_reasons = {}
    for t in trades:
        reason = t.get('exit_reason', 'UNKNOWN')
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    return {
        "total_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(bes),
        "win_rate": win_rate,
        "gross_r": gross_r,
        "net_r": net_r,
        "friction_r": friction_r,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd,
        "max_consecutive_losses": max_consec,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "median_win": median_win,
        "median_loss": median_loss,
        "avg_mfe": float(np.mean(mfe_vals)),
        "median_mfe": float(np.median(mfe_vals)),
        "avg_mae": float(np.mean(mae_vals)),
        "median_mae": float(np.median(mae_vals)),
        "exit_reasons": exit_reasons,
        "r_distribution": r_vals
    }

h0_stats = compute_detailed_stats(h0_trades)
pl_stats = compute_detailed_stats(pl_trades)

print("=== DETAILED STATS SUMMARY ===")
print("METRIC                         | H0         | PROFIT_LOCK | DELTA")
print("-" * 65)
for k in ["total_trades", "wins", "losses", "breakevens", "win_rate", "gross_r", "net_r", "friction_r", "expectancy", "profit_factor", "max_drawdown", "max_consecutive_losses", "avg_win", "avg_loss", "median_win", "median_loss", "avg_mfe", "median_mfe", "avg_mae", "median_mae"]:
    hv = h0_stats[k]
    pv = pl_stats[k]
    d = pv - hv
    if isinstance(hv, float):
        print(f"{k:<30s} | {hv:10.4f} | {pv:11.4f} | {d:+10.4f}")
    else:
        print(f"{k:<30s} | {hv:10d} | {pv:11d} | {d:+10d}")

print("\n=== EXIT REASONS ===")
print("H0 Exit Reasons:", h0_stats['exit_reasons'])
print("PL Exit Reasons:", pl_stats['exit_reasons'])

# Attribution categories:
# A. H0 loss -> experiment positive
# B. H0 loss -> experiment smaller loss
# C. H0 winner -> experiment smaller winner
# D. H0 winner -> experiment larger winner
# E. H0 unchanged
# F. H0 trade exited structurally -> experiment exited via protection
# G. experiment trade exited on initial SL
# H. experiment trade exited through another existing lifecycle rule

h0_by_id = {t['trade_id']: t for t in h0_trades}
pl_by_id = {t['trade_id']: t for t in pl_trades}

cats = {c: [] for c in ["A", "B", "C", "D", "E", "F", "G", "H"]}
for tid, ht in h0_by_id.items():
    pt = pl_by_id.get(tid)
    hr = ht['realized_rr']
    pr = pt['realized_rr'] if pt else None
    
    # Check category
    if hr < 0 and pr is not None and pr > 0:
        cats["A"].append(tid)
    elif hr < 0 and pr is not None and pr < 0 and pr > hr:
        cats["B"].append(tid)
    elif hr > 0 and pr is not None and pr > 0 and pr < hr:
        cats["C"].append(tid)
    elif hr > 0 and pr is not None and pr > hr:
        cats["D"].append(tid)
    elif abs(hr - (pr or 0)) < 1e-5:
        cats["E"].append(tid)
        
    if ht.get('exit_reason') == 'MTF_STRUCTURAL_TRAIL' and pt and pt.get('exit_reason') == 'PROFIT_LOCK_TRAIL':
        cats["F"].append(tid)
    if pt and pt.get('exit_reason') == 'INITIAL_LTF_SL':
        cats["G"].append(tid)
    if pt and pt.get('exit_reason') not in ['INITIAL_LTF_SL', 'PROFIT_LOCK_TRAIL']:
        cats["H"].append(tid)

print("\n=== ATTRIBUTION CATEGORIES ===")
for c, tids in sorted(cats.items()):
    desc = {
        "A": "H0 loss -> experiment positive (winner)",
        "B": "H0 loss -> experiment smaller loss",
        "C": "H0 winner -> experiment smaller winner",
        "D": "H0 winner -> experiment larger winner",
        "E": "H0 unchanged",
        "F": "H0 exited structurally -> experiment exited via protection",
        "G": "Experiment trade exited on initial SL",
        "H": "Experiment trade exited through another lifecycle rule (e.g. MTF structural)"
    }[c]
    print(f"Category {c} ({desc}): Count = {len(tids)}")
    for t in tids:
        print(f"   - {t}")
