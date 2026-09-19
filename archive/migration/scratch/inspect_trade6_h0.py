import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

for t in h0['all_trades']:
    if t['trade_id'] == 'cand_SOL/USDT_UNIFIED_STRATEGY_1649638800':
        print("H0 Trade #6 metadata:")
        print(json.dumps(t['metadata'], indent=2))
        print("realized_rr:", t['realized_rr'])
        print("exit_reason:", t['exit_reason'])
        print("exit_price:", t['exit_price'])
        print("entry_price:", t['entry_price'])
        print("initial_stop_price:", t['initial_stop_price'])
        print("current_stop_price:", t['current_stop_price'])
