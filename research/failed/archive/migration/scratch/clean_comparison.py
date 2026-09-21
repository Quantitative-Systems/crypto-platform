import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
    pl = json.load(f)

print("=== AGGREGATE COMPARISON ===")
for k in ["total_trades", "wins", "losses", "breakevens", "win_rate", "gross_r", "net_r", "friction_r", "expectancy", "profit_factor", "max_drawdown_r", "max_consecutive_losses", "avg_mfe_r", "avg_mae_r"]:
    hv = h0['aggregate_performance'].get(k)
    pv = pl['aggregate_performance'].get(k)
    delta = (pv - hv) if isinstance(hv, (int, float)) and isinstance(pv, (int, float)) else "N/A"
    delta_str = f"{delta:+.4f}" if isinstance(delta, float) else str(delta)
    print(f"{k:<25s} | H0: {str(hv):<10s} | PL: {str(pv):<10s} | Delta: {delta_str}")

print("\n=== TRADE-BY-TRADE SIDE-BY-SIDE ===")
h0_trades = {t['trade_id']: t for t in h0['all_trades']}
pl_trades = {t['trade_id']: t for t in pl['all_trades']}

for i, tid in enumerate(h0_trades.keys(), 1):
    h = h0_trades[tid]
    p = pl_trades.get(tid)
    print(f"\nTrade #{i}: {h['stream_id']} {tid[:40]}")
    print(f"  Direction: {h['direction']} | Entry: {h['entry_price']} | Initial SL: {h['initial_stop_price']}")
    print(f"  H0: Exit={h['exit_price']:.4f} | R={h['realized_rr']:+.4f}R | Reason={h['exit_reason']:<20s} | Dur={h['duration_sec']}s")
    if p:
        p_dur = p.get('duration_sec', p.get('exit_timestamp', 0) - p.get('entry_timestamp', 0))
        delta_r = p['realized_rr'] - h['realized_rr']
        print(f"  PL: Exit={p['exit_price']:.4f} | R={p['realized_rr']:+.4f}R | Reason={p['exit_reason']:<20s} | Dur={p_dur}s | Delta={delta_r:+.4f}R")
    else:
        print(f"  PL: NOT FOUND")
