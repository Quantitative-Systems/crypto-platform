"""Winners' forensics: kz age, context, MFE for freshness-gate risk assessment."""
import json
import sys


def rr(t):
    return float(t.get('realized_r', t.get('realized_rr', 0.0)) or 0.0)


path = sys.argv[1] if len(sys.argv) > 1 else 'scratch/exp_target_structural_01_dev_results.json'
d = json.load(open(path))
trades = d['all_trades']
print('== WINNERS + SCRATCHES: forensics ==')
for t in sorted(trades, key=rr, reverse=True):
    if rr(t) <= 0:
        continue
    prov = t.get('metadata', {}).get('structural_provenance', {})
    from datetime import datetime, timezone
    ts = float(t.get('entry_timestamp', t.get('setup_timestamp', 0)) or 0)
    dts = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d') if ts else '?'
    kz_age_days = None
    if isinstance(prov, dict):
        ki = prov.get('htf_interaction_timestamp') or 0
        kc = prov.get('htf_kz_creation_timestamp') or 0
        if ki and kc and ki > kc:
            kz_age_days = (ki - kc) / 86400.0
    retest_latency_h = None
    if isinstance(prov, dict):
        al = prov.get('mtf_alignment_timestamp') or 0
        rt = prov.get('mtf_retest_timestamp') or 0
        if al and rt and rt > al:
            retest_latency_h = (rt - al) / 3600.0
    react_h = None
    if isinstance(prov, dict):
        rt = prov.get('mtf_retest_timestamp') or 0
        lc = prov.get('ltf_confirmation_timestamp') or 0
        if rt and lc and lc > rt:
            react_h = (lc - rt) / 3600.0
    print(f"  {t.get('trade_id','?')[:42]:42s} {dts} {str(t.get('timeframe_set')):6s} "
          f"dir={str(t.get('directional_permission'))[-4:]:5s} realR={rr(t):+.3f} MFE={float(t.get('mfe_r',0) or 0):.2f} "
          f"ctx={str(prov.get('htf_context','?'))[:12]:12s} mtfEv={str(prov.get('mtf_structural_event','?'))[-14:]:14s} "
          f"kzAge={(f'{kz_age_days:.1f}d' if kz_age_days is not None else 'N/A'):>7s} "
          f"retestLat={(f'{retest_latency_h:.1f}h' if retest_latency_h is not None else 'N/A'):>7s} "
          f"reactLat={(f'{react_h:.1f}h' if react_h is not None else 'N/A'):>6s} "
          f"entry={str(prov.get('ltf_entry_reason','?'))[:26]}")
