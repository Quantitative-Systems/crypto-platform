"""Print management-forensics summary."""
import json

for f in ['scratch/h0_monetization_forensics_summary.json', 'scratch/target_monetization_forensics.json']:
    try:
        d = json.load(open(f))
        print('=' * 60)
        print(f)
        print(json.dumps(d, indent=1)[:2500])
    except Exception as e:
        print(f, 'ERR', e)
