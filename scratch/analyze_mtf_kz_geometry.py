import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
import json
import numpy as np

with open("scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json") as f:
    d = json.load(f)

# Find rejected setups in SOL_SET_4, BTC_SET_4, ETH_SET_4
cands = []
for s in d["stream_results"]:
    if "SET_4" in s["stream_id"]:
        for c in s.get("all_candidates", []):
            if c.get("invalidation_reason") == "REJECT_RR_BELOW_4R":
                cands.append(c)

print(f"Total SET_4 rejected setups: {len(cands)}")

kz_stop_pcts = []
exh_stop_pcts = []
target_pcts = []
potential_rrs = []

for c in cands:
    ep = c.get("ltf_entry_price")
    sl = c.get("ltf_structural_sl")
    tp = c.get("htf_target_price")
    if not ep or not sl or not tp:
        continue
    is_long = (sl < ep)
    exh_dist = abs(ep - sl)
    tp_dist = abs(tp - ep)
    
    exh_pct = (exh_dist / ep) * 100.0
    tp_pct = (tp_dist / ep) * 100.0
    
    # Check if candidate has synthetic or primitive MTF keyzone boundary in metadata
    meta = c.get("metadata", {}) or {}
    kz_low = meta.get("synth_mtf_kz_low")
    kz_high = meta.get("synth_mtf_kz_high")
    
    if is_long and kz_low is not None and kz_low < ep:
        kz_dist = ep - kz_low
        kz_pct = (kz_dist / ep) * 100.0
        pot_rr = tp_dist / kz_dist if kz_dist > 0 else 0.0
        kz_stop_pcts.append(kz_pct)
        exh_stop_pcts.append(exh_pct)
        target_pcts.append(tp_pct)
        potential_rrs.append(pot_rr)
    elif (not is_long) and kz_high is not None and kz_high > ep:
        kz_dist = kz_high - ep
        kz_pct = (kz_dist / ep) * 100.0
        pot_rr = tp_dist / kz_dist if kz_dist > 0 else 0.0
        kz_stop_pcts.append(kz_pct)
        exh_stop_pcts.append(exh_pct)
        target_pcts.append(tp_pct)
        potential_rrs.append(pot_rr)

print(f"Candidates with valid MTF Keyzone boundaries: {len(kz_stop_pcts)}")
if kz_stop_pcts:
    print(f"Exhaustive SL %: Mean={np.mean(exh_stop_pcts):.2f}%, Median={np.median(exh_stop_pcts):.2f}%")
    print(f"MTF Keyzone SL %: Mean={np.mean(kz_stop_pcts):.2f}%, Median={np.median(kz_stop_pcts):.2f}%")
    print(f"Target %:        Mean={np.mean(target_pcts):.2f}%, Median={np.median(target_pcts):.2f}%")
    print(f"Potential RR:    Mean={np.mean(potential_rrs):.2f}R, Median={np.median(potential_rrs):.2f}R")
    print(f"Setups with Potential RR >= 4.0R: {sum(1 for r in potential_rrs if r >= 4.0)} ({sum(1 for r in potential_rrs if r >= 4.0)/len(potential_rrs)*100:.1f}%)")
