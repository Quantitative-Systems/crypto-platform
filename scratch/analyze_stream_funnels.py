import json
from collections import Counter

with open("scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json") as f:
    d = json.load(f)

print(f"{'Stream ID':<12} {'Total Cands':<12} {'Stages Reached':<45} {'Rejection Reasons'}")
print("-" * 100)

for s in d["stream_results"]:
    sid = s["stream_id"]
    cands = s.get("all_candidates", [])
    if not cands:
        print(f"{sid:<12} {0:<12} {'None':<45} {'No candidates generated'}")
        continue
    
    stages = Counter()
    rejections = Counter()
    for c in cands:
        st = c.get("stages_reached", [])
        last_stage = st[-1] if st else "START"
        stages[last_stage] += 1
        rej = c.get("invalidation_reason") or "UNKNOWN"
        rejections[rej] += 1
        
    stage_str = ", ".join(f"{k}:{v}" for k, v in stages.most_common(2))
    rej_str = ", ".join(f"{k}:{v}" for k, v in rejections.most_common(2))
    print(f"{sid:<12} {len(cands):<12} {stage_str:<45} {rej_str}")
