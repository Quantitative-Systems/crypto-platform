import json

with open("scratch/canonical_h0_backtest_dev.json") as f:
    h0 = json.load(f)

with open("scratch/exp_target_structural_01_pure_dev.json") as f:
    exp = json.load(f)

print("=== H0 TRADES (N=29) ===")
for i, t in enumerate(h0["all_trades"]):
    meta = t.get("metadata", {})
    sp = meta.get("structural_provenance", {})
    prov = sp.get("htf_target_provenance", "UNKNOWN")
    print(f"{i+1:2d}. [{t['stream_id']:9s}] dir={t['direction']:5s} entry={t['entry_price']:<9.2f} sl={t['initial_stop_price']:<9.2f} tp={t['target_price']:<9.2f} raw_rr={t['raw_rr']:<5.1f} mfe={t['mfe_r']:<5.2f} mae={t['mae_r']:<5.2f} exit={t['exit_reason']:<20s} net_r={t['net_r']:<6.2f} prov={prov}")

print("\n=== TREATMENT TRADES (N=41) ===")
for i, t in enumerate(exp["all_trades"]):
    meta = t.get("metadata", {})
    sp = meta.get("structural_provenance", {})
    prov = sp.get("htf_target_provenance", "UNKNOWN")
    print(f"{i+1:2d}. [{t['stream_id']:9s}] dir={t['direction']:5s} entry={t['entry_price']:<9.2f} sl={t['initial_stop_price']:<9.2f} tp={t['target_price']:<9.2f} raw_rr={t['raw_rr']:<5.1f} mfe={t['mfe_r']:<5.2f} mae={t['mae_r']:<5.2f} exit={t['exit_reason']:<20s} net_r={t['net_r']:<6.2f} prov={prov}")
