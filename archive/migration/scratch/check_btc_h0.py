import json

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

for r in h0['stream_results']:
    if r['stream_id'] == 'BTC_SET_3':
        print(f"H0 BTC_SET_3 candidates count: {len(r.get('all_candidates', []))}")
        for c in r.get('all_candidates', []):
            if '1635278400' in c.get('candidate_id', ''):
                print(f"H0 Candidate: {c.get('candidate_id')} state={c.get('state')} stages={c.get('stages_reached')}")
