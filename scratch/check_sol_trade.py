import json
from strategy_engine.lifecycle.mtf_trailing_engine import MTFStructuralTrailingEngine

with open('scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json') as f:
    pl = json.load(f)

for t in pl['all_trades']:
    if t['trade_id'] == 'cand_SOL/USDT_UNIFIED_STRATEGY_1649638800':
        print(t)
