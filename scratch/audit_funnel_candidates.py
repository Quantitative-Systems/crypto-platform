import json
from collections import Counter

with open('scratch/anchor2_dev_certified_results.json') as f:
    data = json.load(f)

streams = data.get("stream_results", [])
all_cands = []
for s in streams:
    for c in s.get("all_candidates", []):
        c["stream_id"] = s.get("stream_id")
        all_cands.append(c)

ltf_confirmed = [c for c in all_cands if "RISK_GATE" in c.get("stages_reached", [])]
print(f"Total LTF confirmed (reached RISK_GATE): {len(ltf_confirmed)}")

# Dispositions of the 735 LTF confirmed candidates
dispositions = Counter()
rejections_735 = Counter()
for c in ltf_confirmed:
    state = c.get("state")
    inv = c.get("invalidation_reason")
    dispositions[(state, inv)] += 1
    rejections_735[inv] += 1

print("\nExact disposition breakdown of the 735 LTF-confirmed candidates:")
for (st, inv), cnt in dispositions.most_common():
    print(f"  State: {st:10s} | Invalidation: {str(inv):35s} | Count: {cnt:4d} ({cnt/len(ltf_confirmed)*100:.2f}%)")

print("\nRejections among 735:")
for inv, cnt in rejections_735.most_common():
    print(f"  {str(inv):35s} : {cnt:4d} ({cnt/len(ltf_confirmed)*100:.2f}%)")
