import json

with open('scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json') as f:
    d = json.load(f)

print(f"{'Idx':<4} {'Stream':<10} {'Realized R':<12} {'KZ Age (Days)':<15} {'Retest Latency (Hr)':<20} {'Exit Reason':<25}")
print("-" * 90)

for i, t in enumerate(d['all_trades']):
    sp = t.get('metadata', {}).get('structural_provenance', {})
    kz_create = sp.get('htf_kz_creation_timestamp', 0)
    kz_inter = sp.get('htf_interaction_timestamp', 0)
    kz_age_days = (kz_inter - kz_create) / 86400.0 if (kz_create and kz_inter) else 0.0
    mtf_align = sp.get('mtf_alignment_timestamp', 0)
    mtf_retest = sp.get('mtf_retest_timestamp', 0)
    retest_lat_hr = (mtf_retest - mtf_align) / 3600.0 if (mtf_align and mtf_retest) else 0.0
    r = float(t.get('realized_r', t.get('realized_rr', 0)))
    stream = t.get('stream_id', '')
    reason = t.get('exit_reason', '')
    print(f"{i+1:<4d} {stream:<10s} {r:<+12.4f} {kz_age_days:<15.1f} {retest_lat_hr:<20.1f} {reason:<25s}")
