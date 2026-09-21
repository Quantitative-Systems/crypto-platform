import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

for t in h0['all_trades']:
    mfe = t['metadata'].get('mfe_price', t['entry_price'])
    init_sl = t['initial_stop_price']
    entry = t['entry_price']
    risk = abs(entry - init_sl)
    mfe_r = (mfe - entry) / risk if t['direction'] == 'LONG' else (entry - mfe) / risk
    print(f"{t['stream_id']} {t['trade_id'][:35]}: MFE_R = {mfe_r:.4f}")
