import json
import numpy as np

with open('scratch/anchor2_dev_certified_results.json') as f:
    data = json.load(f)

streams = data.get("stream_results", [])
all_cands = []
for s in streams:
    for c in s.get("all_candidates", []):
        c["stream_id"] = s.get("stream_id")
        all_cands.append(c)

ltf_confirmed = [c for c in all_cands if "RISK_GATE" in c.get("stages_reached", [])]
rr_rejected = [c for c in ltf_confirmed if c.get("invalidation_reason") == "REJECT_RR_BELOW_4R"]

print(f"Total RR < 4R rejected: {len(rr_rejected)}")

missing_entry = sum(1 for c in rr_rejected if not c.get("ltf_entry_price"))
missing_sl = sum(1 for c in rr_rejected if not c.get("ltf_structural_sl"))
missing_tp = sum(1 for c in rr_rejected if not c.get("htf_target_price"))

print(f"Missing entry: {missing_entry}, Missing SL: {missing_sl}, Missing TP: {missing_tp}")

# Compute planned RR for each
planned_rrs = []
for c in rr_rejected:
    entry = c.get("ltf_entry_price")
    sl = c.get("ltf_structural_sl")
    tp = c.get("htf_target_price")
    stop_dist = abs(entry - sl)
    target_dist = abs(tp - entry)
    rr = target_dist / stop_dist if stop_dist > 0 else 0
    planned_rrs.append(rr)

planned_rrs = np.array(planned_rrs)
print("\nPlanned RR Distribution for 671 RR < 4R rejected:")
print(f"  Count: {len(planned_rrs)}")
print(f"  Min: {np.min(planned_rrs):.4f}R")
print(f"  25th Percentile (Q1): {np.percentile(planned_rrs, 25):.4f}R")
print(f"  Median: {np.median(planned_rrs):.4f}R")
print(f"  Mean: {np.mean(planned_rrs):.4f}R")
print(f"  75th Percentile (Q3): {np.percentile(planned_rrs, 75):.4f}R")
print(f"  Max: {np.max(planned_rrs):.4f}R")

# Breakdown of RR buckets among the 671
print("\nRR Buckets among 671:")
print(f"  < 1.0R:     {sum(planned_rrs < 1.0)} ({sum(planned_rrs < 1.0)/len(planned_rrs)*100:.2f}%)")
print(f"  1.0 - 2.0R: {sum((planned_rrs >= 1.0) & (planned_rrs < 2.0))} ({sum((planned_rrs >= 1.0) & (planned_rrs < 2.0))/len(planned_rrs)*100:.2f}%)")
print(f"  2.0 - 2.5R: {sum((planned_rrs >= 2.0) & (planned_rrs < 2.5))} ({sum((planned_rrs >= 2.0) & (planned_rrs < 2.5))/len(planned_rrs)*100:.2f}%)")
print(f"  2.5 - 3.0R: {sum((planned_rrs >= 2.5) & (planned_rrs < 3.0))} ({sum((planned_rrs >= 2.5) & (planned_rrs < 3.0))/len(planned_rrs)*100:.2f}%)")
print(f"  3.0 - 3.5R: {sum((planned_rrs >= 3.0) & (planned_rrs < 3.5))} ({sum((planned_rrs >= 3.0) & (planned_rrs < 3.5))/len(planned_rrs)*100:.2f}%)")
print(f"  3.5 - 4.0R: {sum((planned_rrs >= 3.5) & (planned_rrs < 4.0))} ({sum((planned_rrs >= 3.5) & (planned_rrs < 4.0))/len(planned_rrs)*100:.2f}%)")
