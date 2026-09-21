import json

with open('scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json') as f:
    d2 = json.load(f)

sr = d2.get('stream_results', [])
for s in sr:
    if s.get('stream_id') == 'SOL_SET_4':
        cands = s.get('all_candidates', [])
        print(f"Total SOL_SET_4 candidates: {len(cands)}")
        feb_cands = [c for c in cands if 1612137600 <= c.get('creation_timestamp', 0) <= 1614556800]
        print(f"Feb 2021 candidates: {len(feb_cands)}")
        for c in feb_cands:
            cid = c.get('candidate_id')
            st = c.get('state')
            inv = c.get('invalidation_reason')
            cts = c.get('creation_timestamp')
            its = c.get('invalidation_timestamp')
            print(f"  {cid} | State={st} | Reason={inv} | Created={cts} | Inval={its}")
