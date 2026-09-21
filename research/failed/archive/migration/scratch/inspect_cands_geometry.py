import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

cands_with_geometry = []
for sr in d1["stream_results"]:
    stream_id = sr["stream_id"]
    sym = sr["asset"] + "/USDT"
    st = sr["timeframe_set"]
    for c in sr.get("all_candidates", []):
        ep = c.get("ltf_entry_price")
        sl = c.get("ltf_structural_sl")
        tp = c.get("htf_target_price")
        ts = c.get("ltf_confirmation_timestamp")
        stages = c.get("stages_reached", [])
        if "RISK_GATE" in stages or (ep and sl and tp and ts):
            cands_with_geometry.append({
                "candidate_id": c.get("candidate_id"),
                "stream_id": stream_id,
                "symbol": sym,
                "timeframe_set": st,
                "direction": c.get("mtf_setup_direction") or c.get("htf_macro_direction"),
                "entry_price": ep,
                "stop_price": sl,
                "target_price": tp,
                "confirmation_ts": ts,
                "state": c.get("state"),
                "invalidation_reason": c.get("invalidation_reason"),
                "stages": stages,
                "mtf_event": c.get("mtf_structural_event"),
                "mtf_keyzone": c.get("mtf_keyzone_id"),
                "htf_keyzone": c.get("htf_keyzone_id"),
                "htf_target_prov": c.get("htf_target_provenance"),
                "htf_phase": c.get("htf_phase"),
                "mtf_align_ts": c.get("mtf_alignment_timestamp"),
                "mtf_retest_ts": c.get("mtf_retest_timestamp"),
                "ltf_entry_reason": c.get("ltf_entry_reason")
            })

print(f"Total candidates with geometry / reached RISK_GATE: {len(cands_with_geometry)}")
by_inv = {}
for cg in cands_with_geometry:
    inv = cg["invalidation_reason"] or "ENTERED/PASSED"
    by_inv[inv] = by_inv.get(inv, 0) + 1
for k, v in sorted(by_inv.items(), key=lambda x: -x[1]):
    print(f"  {k:<35}: {v:3d}")
