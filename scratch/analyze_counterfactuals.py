import json
import numpy as np

with open("scratch/adu01_counterfactual_sim_results.json") as f:
    data = json.load(f)

print(f"Total simulated candidates: {len(data)}")

# Decompose by invalidation_reason
by_reason = {}
for d in data:
    r = d["invalidation_reason"]
    if r not in by_reason:
        by_reason[r] = []
    by_reason[r].append(d)

print("=" * 90)
print(f"{'Group / Invalidation Reason':<35} | {'N':<5} | {'Hit TP':<7} | {'Hit SL':<7} | {'MFE>=1R':<8} | {'MFE>=2R':<8} | {'Med MFE':<8} | {'Med MAE':<8}")
print("-" * 90)

for r, cands in sorted(by_reason.items(), key=lambda x: -len(x[1])):
    n = len(cands)
    tp_count = sum(1 for c in cands if c["hit_target"])
    sl_count = sum(1 for c in cands if c["hit_stop"])
    mfe_10 = sum(1 for c in cands if c["mfe_10"])
    mfe_20 = sum(1 for c in cands if c["mfe_20"])
    mfes = [c["mfe_r"] for c in cands]
    maes = [c["mae_r"] for c in cands]
    
    print(f"{r:<35} | {n:<5} | {tp_count:2d} ({tp_count/n*100:4.1f}%) | {sl_count:2d} ({sl_count/n*100:4.1f}%) | {mfe_10:2d} ({mfe_10/n*100:4.1f}%) | {mfe_20:2d} ({mfe_20/n*100:4.1f}%) | {np.median(mfes):5.2f}R | {np.median(maes):5.2f}R")

print("=" * 90)

# Decompose by Outcome Class across ALL candidates
classes = {"A_STRONG": [], "B_MODERATE": [], "C_WEAK": [], "D_IMMEDIATE_FAILURE": []}
for c in data:
    m = c["mfe_r"]
    if c["hit_target"] or m >= 2.0:
        classes["A_STRONG"].append(c)
    elif m >= 1.0:
        classes["B_MODERATE"].append(c)
    elif m >= 0.5:
        classes["C_WEAK"].append(c)
    else:
        classes["D_IMMEDIATE_FAILURE"].append(c)

print("\nOUTCOME CLASSES ACROSS ALL CANDIDATES AT RISK GATE:")
for k, v in classes.items():
    print(f"  {k:<22}: {len(v):3d} ({len(v)/len(data)*100:5.1f}%)")
