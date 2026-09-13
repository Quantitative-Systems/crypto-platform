import json

with open("scratch/d0_forensic_records.json") as f:
    recs = json.load(f)

print("=== DETAILED FORENSIC ATTRIBUTION OF 20 C1 LOSSES ===")

for r in recs[:10]:
    print(f"\n--- Trade #{r['rank']:02d} [T{r['orig_trade_idx']:02d}] {r['symbol']} ({r['tf_set']}) ---")
    print(f"  Direction: {r['direction']} | Net R: {r['net_r']:.4f} | Exit: {r['exit_reason']}")
    print(f"  A. MFE: {r['mfe_r']:.2f}R ({r['mfe_cat']}) | MAE: {r['mae_r']:.2f}R")
    print(f"  B. MFE Timing: {r['mfe_timing']} | Duration: {r['duration_min']} min")
    print(f"  C. MFE-to-Exit Behavior: {r['exit_behavior']}")
    print(f"  D. MTF Setup Quality:")
    print(f"     - Shift Event: {r['mtf_event']}")
    print(f"     - MTF Displacement: {r['mtf_displacement_pct']:.2f}%")
    print(f"     - MTF Keyzone ID: {r['mtf_kz_id']}")
    print(f"     - Align-to-Retest: {r['align_to_retest_min']} min | KZ-to-Retest: {r['kz_to_retest_min']} min")
    print(f"  E. LTF Trigger:")
    print(f"     - Reason: {r['ltf_trigger_reason']}")
    print(f"     - Retest-to-Entry: {r['retest_to_entry_min']} min")
    print(f"     - Risk Dist: {r['risk_dist']:.4f} ({r['risk_pct']:.2f}%)")
    print(f"     - Local Sweep: {r['sweep_detected']} | LTF Disp: {r['ltf_disp_pct']:.2f}% (Body Ratio: {r['ltf_body_ratio']:.2f})")
    print(f"  F. HTF Context:")
    print(f"     - HTF KZ: {r['htf_kz_id']}")
    print(f"     - HTF Target: {r['htf_target_prov']} @ {r['target_p']}")
    print(f"     - Planned RR: {r['raw_rr']:.2f}R | Phase: {r['htf_phase']}")
    print(f"  G. Regime: Trend={r['trend_regime']} | Vol={r['vol_regime']} | Phase={r['mkt_phase']}")
