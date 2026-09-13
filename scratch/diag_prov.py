"""Print full structural provenance of representative trades from a results file."""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'scratch/exp_target_structural_01_dev_results.json'
d = json.load(open(path))
trades = d['all_trades']
keys = set()
for t in trades:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    if isinstance(prov, dict):
        keys.update(prov.keys())
print('provenance keys:', sorted(keys))
print()
# Show provenance of: one win with expansion target, one BE trade, one loss
shown = 0
seen_types = set()
for t in trades:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    tgt = str(prov.get('htf_target_provenance', '?')) if isinstance(prov, dict) else '?'
    tag = t.get('exit_reason', '?')
    sig = (tag, tgt.split('_')[0] if tgt else '?')
    if sig in seen_types:
        continue
    seen_types.add(sig)
    print('=' * 70)
    print(t.get('trade_id'), '| exit:', tag, '| realized:', t.get('realized_r', t.get('realized_rr')))
    print(json.dumps(prov, indent=1)[:3000])
    shown += 1
    if shown >= 5:
        break
