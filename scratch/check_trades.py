import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

print(f"H0 Total trades: {len(h0['all_trades'])}")
for t in h0['all_trades']:
    print(f"H0: {t.get('stream_id')} {t['trade_id']} entry={t.get('entry_timestamp')} exit={t.get('exit_timestamp')} dur={t.get('duration_sec', (t.get('exit_timestamp',0)-t.get('entry_timestamp',0)))} realized_rr={t['realized_rr']:.4f} exit_reason={t['exit_reason']}")

try:
    with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
        pl = json.load(f)
    print(f"\nPrior Profit Lock Total trades: {len(pl['all_trades'])}")
    for t in pl['all_trades']:
        print(f"PL: {t.get('stream_id')} {t['trade_id']} entry={t.get('entry_timestamp')} exit={t.get('exit_timestamp')} dur={t.get('duration_sec', (t.get('exit_timestamp',0)-t.get('entry_timestamp',0)))} realized_rr={t['realized_rr']:.4f} exit_reason={t['exit_reason']}")
except Exception as e:
    print(f"Could not read prior profit lock: {e}")
