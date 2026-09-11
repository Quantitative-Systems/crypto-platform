import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
    pl = json.load(f)

print(f"=== H0 Aggregate Performance ===")
print(json.dumps(h0['aggregate_performance'], indent=2))

print(f"\n=== PROFIT_LOCK_0.5R_0.25R Aggregate Performance ===")
print(json.dumps(pl['aggregate_performance'], indent=2))

print(f"\n=== Trade-by-Trade Comparison ===")
h0_trades = {t['trade_id']: t for t in h0['all_trades']}
pl_trades = {t['trade_id']: t for t in pl['all_trades']}

all_ids = list(dict.fromkeys(list(h0_trades.keys()) + list(pl_trades.keys())))
for tid in all_ids:
    h = h0_trades.get(tid)
    p = pl_trades.get(tid)
    print(f"\nTrade ID: {tid}")
    if h:
        print(f"  H0: stream={h.get('stream_id')} dir={h['direction']} entry={h.get('entry_timestamp')} exit={h.get('exit_timestamp')} dur={h.get('duration_sec', h.get('exit_timestamp',0)-h.get('entry_timestamp',0))}s R={h['realized_rr']:.4f} reason={h['exit_reason']}")
    else:
        print("  H0: NOT EXECUTED")
    if p:
        print(f"  PL: stream={p.get('stream_id')} dir={p['direction']} entry={p.get('entry_timestamp')} exit={p.get('exit_timestamp')} dur={p.get('duration_sec', p.get('exit_timestamp',0)-p.get('entry_timestamp',0))}s R={p['realized_rr']:.4f} reason={p['exit_reason']}")
    else:
        print("  PL: NOT EXECUTED")

# Check why BTC_SET_3 trade was missing in PL:
for r in pl['stream_results']:
    if r['stream_id'] == 'BTC_SET_3':
        print(f"\nBTC_SET_3 candidates count: {len(r.get('all_candidates', []))}")
        for c in r.get('all_candidates', []):
            print(f"Candidate: {c.get('candidate_id')} state={c.get('state')} stages={c.get('stages_reached')}")
