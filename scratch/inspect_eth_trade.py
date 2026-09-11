import json

with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
    pl = json.load(f)

for t in pl['all_trades']:
    if t['stream_id'] == 'ETH_SET_3':
        print(json.dumps(t, indent=2))
