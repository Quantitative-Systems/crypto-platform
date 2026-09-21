import json
import numpy as np

with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
    d = json.load(f)

all_cands = []
for s in d.get("stream_results", []):
    all_cands.extend(s.get("all_candidates", []))

risk_cands = [c for c in all_cands if "RISK_GATE" in c.get("stages_reached", [])]
print(f"Total Candidates Reaching RISK_GATE: {len(risk_cands)}")

reasons = {}
for c in risk_cands:
    r = c.get("invalidation_reason")
    reasons[r] = reasons.get(r, 0) + 1
print("Invalidation Reasons for candidates reaching RISK_GATE:")
for r, cnt in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
    print(f"  {r}: {cnt} ({cnt/len(risk_cands)*100:.2f}%)")

# Calculate planned RR for all 391 candidates
rrs = []
rrs_by_set = {"SET_1": [], "SET_2": [], "SET_3": [], "SET_4": []}
target_types = {}

for c in risk_cands:
    tf_set = c.get("candidate_id").split("_")[1] # or stream
    # Extract timeframe set from candidate_id or stream
    ep = c.get("ltf_entry_price")
    sl = c.get("ltf_structural_sl")
    tp = c.get("htf_target_price")
    prov = c.get("htf_target_provenance", "UNKNOWN")
    target_types[prov] = target_types.get(prov, 0) + 1
    
    if ep and sl and tp and tp > 0:
        s_dist = abs(ep - sl)
        t_dist = abs(tp - ep)
        if s_dist > 0:
            rr = t_dist / s_dist
            rrs.append(rr)
            for s in ["SET_1", "SET_2", "SET_3", "SET_4"]:
                if s in c.get("candidate_id", "") or s in c.get("htf_context_id", ""):
                    rrs_by_set[s].append(rr)

print(f"\nCandidates with computable positive planned RR: {len(rrs)} / {len(risk_cands)}")
print("Planned RR Distribution Statistics:")
print(f"  Mean:   {np.mean(rrs):.2f}R")
print(f"  Median: {np.median(rrs):.2f}R")
print(f"  Min:    {np.min(rrs):.2f}R")
print(f"  Max:    {np.max(rrs):.2f}R")
print(f"  P25:    {np.percentile(rrs, 25):.2f}R")
print(f"  P75:    {np.percentile(rrs, 75):.2f}R")
print(f"  P90:    {np.percentile(rrs, 90):.2f}R")

bins = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, float('inf')]
bin_labels = ["<0.5R", "0.5-1.0R", "1.0-1.5R", "1.5-2.0R", "2.0-2.5R", "2.5-3.0R", "3.0-3.5R", "3.5-4.0R", ">=4.0R"]
counts, _ = np.histogram(rrs, bins=bins)

print("\nPlanned RR Histogram:")
for label, cnt in zip(bin_labels, counts):
    pct = cnt / len(rrs) * 100.0
    print(f"  {label:<10s}: {cnt:3d} ({pct:5.1f}%)")

print("\nTarget Provenance Breakdown for RISK_GATE Candidates:")
for prov, cnt in sorted(target_types.items(), key=lambda x: x[1], reverse=True):
    print(f"  {prov:<35s}: {cnt:3d} ({cnt/len(risk_cands)*100:.1f}%)")
