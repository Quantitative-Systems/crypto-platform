import json
import numpy as np

with open("scratch/adu01_counterfactual_sim_results.json") as f:
    data = json.load(f)

# Filter for candidates that passed valid geometry or were entered/passed
cands = [d for d in data if d["invalidation_reason"] in ["ENTERED/PASSED", "REJECT_RR_BELOW_4R"]]
print(f"Analyzing {len(cands)} candidates with valid geometry at RISK_GATE...")

for c in cands:
    ts = c["confirmation_ts"]
    c["year"] = 2021 if ts < 1640995200 else 2022
    
    # Archetype classification
    trig = c.get("ltf_entry_reason", "")
    if "SWEEP" in trig:
        c["archetype"] = "ARCH_B_SWEEP_DISP"
    elif "DISPLACEMENT" in trig:
        c["archetype"] = "ARCH_A_IMMEDIATE_DISP"
    else:
        c["archetype"] = "ARCH_C_STRUCTURAL"
        
    # Latency: Align to Retest
    a_ts = c.get("mtf_align_ts", 0)
    r_ts = c.get("mtf_retest_ts", 0)
    if a_ts and r_ts and r_ts >= a_ts:
        c["align_to_retest_hr"] = (r_ts - a_ts) / 3600.0
    else:
        c["align_to_retest_hr"] = 0.0
        
    # Latency: Retest to Confirmation
    if r_ts and ts and ts >= r_ts:
        c["retest_to_conf_hr"] = (ts - r_ts) / 3600.0
    else:
        c["retest_to_conf_hr"] = 0.0
        
    # Outcome bucket
    mfe = c["mfe_r"]
    if c["hit_target"] or mfe >= 2.0:
        c["class"] = "A_STRONG"
    elif mfe >= 1.0:
        c["class"] = "B_MODERATE"
    elif mfe >= 0.5:
        c["class"] = "C_WEAK"
    else:
        c["class"] = "D_FAIL"

# 1. Analysis by Archetype
print("\n" + "=" * 90)
print("ENTRY ARCHETYPE ANALYSIS (Continuation vs Reversal)")
print("=" * 90)
by_arch = {}
for c in cands:
    a = c["archetype"]
    if a not in by_arch: by_arch[a] = []
    by_arch[a].append(c)

for a, clist in sorted(by_arch.items()):
    n = len(clist)
    strong = sum(1 for x in clist if x["class"] == "A_STRONG")
    fail = sum(1 for x in clist if x["class"] == "D_FAIL")
    med_mfe = np.median([x["mfe_r"] for x in clist])
    print(f"Archetype: {a:<25} | N={n:3d} | Strong (>=2R): {strong:2d} ({strong/n*100:4.1f}%) | Fail (<0.5R): {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")

# 2. Archetype conditioned on HTF Phase
print("\n" + "-" * 90)
print("ARCHETYPE CONDITIONED ON HTF PHASE (EXPANSION vs PULLBACK)")
print("-" * 90)
for a in ["ARCH_A_IMMEDIATE_DISP", "ARCH_B_SWEEP_DISP"]:
    for phase in ["MarketPhase.EXPANSION", "MarketPhase.PULLBACK"]:
        sub = [x for x in cands if x["archetype"] == a and x["htf_phase"] == phase]
        if sub:
            n = len(sub)
            strong = sum(1 for x in sub if x["class"] == "A_STRONG")
            fail = sum(1 for x in sub if x["class"] == "D_FAIL")
            med_mfe = np.median([x["mfe_r"] for x in sub])
            print(f"  {a:<22} + {phase.replace('MarketPhase.', ''):<10} | N={n:2d} | Strong: {strong:2d} ({strong/n*100:4.1f}%) | Fail: {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")

# 3. Retest Latency Separation (Align to Retest)
print("\n" + "=" * 90)
print("RETEST LATENCY ANALYSIS (Align-to-Retest Latency)")
print("=" * 90)
# Group into Fast (<6h), Moderate (6-24h), Stale (>24h)
for label, (min_h, max_h) in [("Fast (<6h)", (0, 6)), ("Moderate (6-24h)", (6, 24)), ("Stale (>24h)", (24, 999999))]:
    sub = [x for x in cands if min_h <= x["align_to_retest_hr"] < max_h]
    n = len(sub)
    if n:
        strong = sum(1 for x in sub if x["class"] == "A_STRONG")
        fail = sum(1 for x in sub if x["class"] == "D_FAIL")
        med_mfe = np.median([x["mfe_r"] for x in sub])
        print(f"  Retest Latency {label:<18} | N={n:3d} | Strong: {strong:2d} ({strong/n*100:4.1f}%) | Fail: {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")

# 4. Reaction Latency Separation (Retest to Confirmation)
print("\n" + "-" * 90)
print("REACTION SPEED ANALYSIS (Retest-to-Confirmation Latency)")
print("-" * 90)
for label, (min_h, max_h) in [("Immediate (<2h)", (0, 2)), ("Normal (2-8h)", (2, 8)), ("Delayed (>8h)", (8, 999999))]:
    sub = [x for x in cands if min_h <= x["retest_to_conf_hr"] < max_h]
    n = len(sub)
    if n:
        strong = sum(1 for x in sub if x["class"] == "A_STRONG")
        fail = sum(1 for x in sub if x["class"] == "D_FAIL")
        med_mfe = np.median([x["mfe_r"] for x in sub])
        print(f"  Reaction Speed {label:<18} | N={n:3d} | Strong: {strong:2d} ({strong/n*100:4.1f}%) | Fail: {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")

# 5. Zone Type Separation
print("\n" + "=" * 90)
print("MTF ZONE TYPE SEPARATION")
print("=" * 90)
by_kz = {"FVG": [], "OB": [], "SYNTH": []}
for c in cands:
    kz = str(c.get("mtf_keyzone", ""))
    if "FVG" in kz: by_kz["FVG"].append(c)
    elif "OB" in kz: by_kz["OB"].append(c)
    elif "synth" in kz: by_kz["SYNTH"].append(c)

for kz_type, sub in by_kz.items():
    n = len(sub)
    if n:
        strong = sum(1 for x in sub if x["class"] == "A_STRONG")
        fail = sum(1 for x in sub if x["class"] == "D_FAIL")
        med_mfe = np.median([x["mfe_r"] for x in sub])
        print(f"  MTF Zone Type {kz_type:<10} | N={n:3d} | Strong: {strong:2d} ({strong/n*100:4.1f}%) | Fail: {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")

# 6. MTF Alignment Event Separation
print("\n" + "=" * 90)
print("MTF ALIGNMENT EVENT SEPARATION")
print("=" * 90)
by_mtf = {}
for c in cands:
    e = str(c.get("mtf_event", "")).replace("EventType.", "")
    if e not in by_mtf: by_mtf[e] = []
    by_mtf[e].append(c)

for e, sub in sorted(by_mtf.items()):
    n = len(sub)
    strong = sum(1 for x in sub if x["class"] == "A_STRONG")
    fail = sum(1 for x in sub if x["class"] == "D_FAIL")
    med_mfe = np.median([x["mfe_r"] for x in sub])
    print(f"  MTF Event {e:<20} | N={n:3d} | Strong: {strong:2d} ({strong/n*100:4.1f}%) | Fail: {fail:2d} ({fail/n*100:4.1f}%) | Med MFE: {med_mfe:4.2f}R")
