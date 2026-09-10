import json
from collections import Counter

with open('scratch/canonical_735_opportunity_ledger.json') as f:
    ledger = json.load(f)

print('--- ASSET BREAKDOWN ---')
asset_counts = Counter(r['symbol'].split('/')[0] for r in ledger)
for a, c in asset_counts.most_common():
    print(f'  {a}: {c} ({c/len(ledger)*100:.2f}%)')

print('\n--- TIMEFRAME SET BREAKDOWN ---')
tf_counts = Counter(r['timeframe_set'] for r in ledger)
for tf, c in tf_counts.most_common():
    print(f'  {tf}: {c} ({c/len(ledger)*100:.2f}%)')

print('\n--- DIRECTION BREAKDOWN ---')
dir_counts = Counter(r['direction'] for r in ledger)
for d, c in dir_counts.most_common():
    print(f'  {d}: {c} ({c/len(ledger)*100:.2f}%)')

print('\n--- STREAM BREAKDOWN ---')
stream_counts = Counter(r['stream_id'] for r in ledger)
for s, c in sorted(stream_counts.items()):
    sub = [r for r in ledger if r['stream_id'] == s]
    rr_rej = sum(1 for r in sub if r['final_disposition'] == 'RR_LT_4R_REJECTION')
    app = sum(1 for r in sub if r['passed_target_resolution'])
    print(f'  {s:10s}: Total={c:3d} | RR<4R={rr_rej:3d} | TargetResolved={app:2d}')
