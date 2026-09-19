import json
import numpy as np

with open("scratch/adu01_counterfactual_sim_results.json") as f:
    all_data = json.load(f)

# Candidates that passed RISK_GATE or entered
cands = [d for d in all_data if d["invalidation_reason"] in ["ENTERED/PASSED", "REJECT_RR_BELOW_4R"]]

for c in cands:
    ts = c["confirmation_ts"]
    c["year"] = 2021 if ts < 1640995200 else 2022
    
    # Latencies
    a_ts = c.get("mtf_align_ts", 0)
    r_ts = c.get("mtf_retest_ts", 0)
    c["align_to_retest_hr"] = (r_ts - a_ts) / 3600.0 if (a_ts and r_ts and r_ts >= a_ts) else 0.0
    c["retest_to_conf_hr"] = (ts - r_ts) / 3600.0 if (r_ts and ts and ts >= r_ts) else 0.0
    
    # Archetype
    trig = c.get("ltf_entry_reason", "")
    c["archetype"] = "SWEEP" if "SWEEP" in trig else "DISP"
    
    # Stop distance pct
    ep = c["entry_price"]
    sl = c["stop_price"]
    c["stop_pct"] = abs(ep - sl) / ep * 100.0 if ep else 0.0

# -------------------------------------------------------------
# Construct Deterministic Composite Setup-Quality Scoring Model
# Components (strictly integer points, 0 to 5 max):
# 1. Zone Freshness (Retest Latency):
#    - Align->Retest <= 12h: +2 pts (Fresh)
#    - Align->Retest 12h-24h: +1 pt (Moderate)
#    - Align->Retest > 24h: 0 pts (Stale)
# 2. Reaction Speed:
#    - Retest->Confirmation <= 4h: +1 pt (Decisive reaction)
#    - Retest->Confirmation > 4h: 0 pts (Absorption/lingering)
# 3. Stop Geometry Quality:
#    - Stop distance between 0.8% and 2.5%: +1 pt (Healthy structural stop)
#    - Stop distance < 0.8% (fragile noise) or > 2.5% (oversized): 0 pts
# 4. Context Synergy:
#    - If Archetype is SWEEP, or if MTF shift is EXTERNAL_CHOCH/MSS: +1 pt
# -------------------------------------------------------------

def compute_quality_score(c):
    score = 0
    # 1. Zone Freshness
    if c["align_to_retest_hr"] <= 12.0:
        score += 2
    elif c["align_to_retest_hr"] <= 24.0:
        score += 1
        
    # 2. Reaction Speed
    if c["retest_to_conf_hr"] <= 4.0:
        score += 1
        
    # 3. Stop Geometry
    if 0.8 <= c["stop_pct"] <= 2.5:
        score += 1
        
    # 4. Context Synergy
    mtf = str(c.get("mtf_event", ""))
    if c["archetype"] == "SWEEP" or "CHOCH" in mtf or "MSS" in mtf:
        score += 1
        
    return score

for c in cands:
    c["quality_score"] = compute_quality_score(c)

print(f"Total evaluated candidates: {len(cands)}")
print("Score distribution:", {sc: sum(1 for c in cands if c['quality_score'] == sc) for sc in range(6)})

# Test separation across score thresholds on 2021 (Discovery) vs 2022 (Confirmation)
def test_partition(year_label, year_val, threshold=3):
    sub_all = [c for c in cands if c["year"] == year_val]
    sub_filtered = [c for c in sub_all if c["quality_score"] >= threshold]
    
    n_all = len(sub_all)
    n_fil = len(sub_filtered)
    
    strong_all = sum(1 for c in sub_all if c["hit_target"] or c["mfe_r"] >= 2.0)
    strong_fil = sum(1 for c in sub_filtered if c["hit_target"] or c["mfe_r"] >= 2.0)
    
    fail_all = sum(1 for c in sub_all if c["mfe_r"] < 0.5)
    fail_fil = sum(1 for c in sub_filtered if c["mfe_r"] < 0.5)
    
    med_mfe_all = np.median([c["mfe_r"] for c in sub_all]) if sub_all else 0.0
    med_mfe_fil = np.median([c["mfe_r"] for c in sub_filtered]) if sub_filtered else 0.0
    
    print(f"\n=== {year_label} PARTITION (Year={year_val}) ===")
    print(f"  All Candidates at Risk Gate: N={n_all:3d} | Strong (>=2R): {strong_all:2d} ({strong_all/n_all*100:4.1f}%) | Fail (<0.5R): {fail_all:2d} ({fail_all/n_all*100:4.1f}%) | Med MFE: {med_mfe_all:4.2f}R")
    print(f"  Score >= {threshold} Filtered:      N={n_fil:3d} | Strong (>=2R): {strong_fil:2d} ({strong_fil/n_fil*100:4.1f}%) | Fail (<0.5R): {fail_fil:2d} ({fail_fil/n_fil*100:4.1f}%) | Med MFE: {med_mfe_fil:4.2f}R")

test_partition("DISCOVERY (2021)", 2021, threshold=4)
test_partition("CONFIRMATION (2022)", 2022, threshold=4)
