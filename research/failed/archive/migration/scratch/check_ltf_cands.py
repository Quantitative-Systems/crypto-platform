import json

with open("scratch/exp_d1_dev.json") as f:
    d = json.load(f)

cands_with_ltf = []
for r in d.get("stream_results", []):
    for c in r.get("all_candidates", []):
        if c.get("ltf_confirmation_timestamp", 0) > 0:
            cands_with_ltf.append(c)

print(f"Total candidates with LTF confirmation: {len(cands_with_ltf)}")
states = {}
reasons = {}
for c in cands_with_ltf:
    st = c.get("state")
    states[st] = states.get(st, 0) + 1
    inv = c.get("invalidation_reason", "NONE")
    reasons[inv] = reasons.get(inv, 0) + 1

print("States of confirmed candidates:", states)
print("Invalidation reasons of confirmed candidates:", reasons)
