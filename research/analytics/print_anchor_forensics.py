import json

with open("/home/mrcn2/crypto-platform/scratch/forensic_candidate_ledger.json") as f:
    d = json.load(f)

print("=" * 120)
print("ANCHOR FORENSICS (REJECT_MISSING_STRUCTURAL_ANCHORS & REJECT_INVALID_ANCHOR_GEOMETRY)")
print("=" * 120)

for idx, c in enumerate(d["candidates_ledger"], 1):
    reason = c["exact_rejection_reason"]
    if reason in ["REJECT_MISSING_STRUCTURAL_ANCHORS", "REJECT_INVALID_ANCHOR_GEOMETRY", "REJECT_RR_BELOW_4R"]:
        anch = c["anchor_details"]
        print(f"[{idx:02d}] ID: {c['candidate_id']} | Dir: {c['direction']:12s} | Reason: {reason}")
        print(f"     Entry: {anch['ltf_current_price']} | Protected Low: {anch['ltf_protected_low_price']} | Protected High: {anch['ltf_protected_high_price']} | HTF Target: {anch['htf_target_price']}")
        print(f"     Raw RR: {c['raw_rr']} | LTF Swings: {anch['ltf_swings_count']} | LTF Trend: {anch['ltf_external_trend']}")
        print("-" * 120)

print("\n" + "=" * 120)
print("TTL FORENSICS (REJECT_SETUP_LIFESPAN_EXPIRED)")
print("=" * 120)

for idx, c in enumerate(d["candidates_ledger"], 1):
    reason = c["exact_rejection_reason"]
    if reason == "REJECT_SETUP_LIFESPAN_EXPIRED":
        print(f"[{idx:02d}] ID: {c['candidate_id']} | Dir: {c['direction']:12s}")
        print(f"     Created: {c['creation_timestamp']} | MTF Align: {c['mtf_alignment_timestamp']} | MTF Retest: {c['mtf_retest_timestamp']}")
        print(f"     LTF Bars Evaluated: {c['ltf_eval_bars_count']} | Sweep Detected: {c['ltf_sweep_detected']} | Disp Detected: {c['ltf_displacement_detected']}")
        print("-" * 120)
