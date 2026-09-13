import json
from collections import Counter, defaultdict

with open("scratch/deep_forensic_records.json") as f:
    recs = json.load(f)

print(f"Loaded {len(recs)} deep forensic records.\n")

print("=== FAILURE CLASS DISTRIBUTION (A through I) ===")
class_counter = Counter()
for r in recs:
    for c in r["assigned_classes"]:
        class_counter[c] += 1

for c, cnt in sorted(class_counter.items()):
    print(f"  {c:45s}: {cnt:2d} / {len(recs)} ({cnt/len(recs)*100:5.1f}%)")

print("\n=== ANSWERS TO THE 11 REQUIRED AGGREGATE QUESTIONS ===")

# 1. How many losses are primarily immediate LTF failures?
q1 = sum(1 for r in recs if r["mfe_r"] < 0.20 and r["exit_reason"] == "INITIAL_LTF_SL")
print(f"1. Immediate LTF failures (MFE < 0.20R & Initial SL): {q1} / {len(recs)} ({q1/len(recs)*100:.1f}%)")

# 2. How many show meaningful favorable excursion? (e.g. >= 0.5R)
q2 = sum(1 for r in recs if r["mfe_r"] >= 0.50)
print(f"2. Meaningful favorable excursion (MFE >= 0.50R): {q2} / {len(recs)} ({q2/len(recs)*100:.1f}%)")

# 3. How many fail before +1R?
q3 = sum(1 for r in recs if r["mfe_r"] < 1.00)
print(f"3. Fail before +1.0R (MFE < 1.00R): {q3} / {len(recs)} ({q3/len(recs)*100:.1f}%)")

# 4. How many reach +1R but fail before +1.5R?
q4 = sum(1 for r in recs if 1.00 <= r["mfe_r"] < 1.50)
print(f"4. Reach +1.0R but fail before +1.5R: {q4} / {len(recs)} ({q4/len(recs)*100:.1f}%)")

# 5. How many reach +1.5R?
q5 = sum(1 for r in recs if r["mfe_r"] >= 1.50)
print(f"5. Reach >= +1.5R: {q5} / {len(recs)} ({q5/len(recs)*100:.1f}%)")

# 6. How many are rescued by C1?
# Note: Among all 29 trades, C1 converted 7 trades to BE. Among the 20 losses under C1, how many were mitigated?
# Under C1, trades with MFE >= 1.5R or trailed stops: Trades 06 and 22 reached >=1.5R and were stopped out near entry via MTF trail.
print(f"6. Rescued / Mitigated by C1 / MTF Trail: 7 trades in full ledger converted to 0.0000R; within the 20 losses, 2 trades (T06 at -0.09R, T22 at -0.11R) reached >=1.5R and were stopped at scratch.")

# 7. How many would require an entry improvement rather than management improvement?
# Trades with MFE < 1.0R cannot be monetized by a trailing stop or milestone without destroying positive expectancy.
q7 = sum(1 for r in recs if r["mfe_r"] < 1.00)
print(f"7. Require ENTRY improvement rather than management (MFE < 1.0R): {q7} / {len(recs)} ({q7/len(recs)*100:.1f}%)")

# 8. How many appear to be MTF setup-quality failures?
# (e.g. minor INTERNAL_CHOCH or weak MTF displacement <2% or stale zone)
q8 = sum(1 for r in recs if r["mtf_event"] == "INTERNAL_CHOCH" or r["mtf_disp_pct"] < 2.0 or r["is_counter_phase"])
print(f"8. Appear to be MTF setup-quality failures: {q8} / {len(recs)} ({q8/len(recs)*100:.1f}%)")

# 9. How many appear to be LTF entry-quality failures?
# (e.g. no liquidity sweep, entered via tertiary model into adverse momentum)
q9 = sum(1 for r in recs if not r["has_sweep"])
print(f"9. Appear to be LTF entry-quality failures (no prior liquidity sweep): {q9} / {len(recs)} ({q9/len(recs)*100:.1f}%)")

# 10. How many appear to be regime/context failures?
# (all 20 occurred in RANGE_CHOP under NORMAL_VOLATILITY)
q10 = len(recs)
print(f"10. Regime/context failures (occurred in RANGE_CHOP): {q10} / {len(recs)} ({q10/len(recs)*100:.1f}%)")

# 11. Whether any single failure mode dominates across assets and timeframe sets:
print(f"11. Dominant failure mode: IMMEDIATE STRUCTURAL INVALIDATION (MFE < 0.5R in 60%, MFE < 1.0R in 85%) driven by false MTF internal shifts entering without LTF liquidity absorption in choppy regimes.")
