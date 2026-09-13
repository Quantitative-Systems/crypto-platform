"""Forensic breakdown of losers + context distribution for a results file."""
import json
import sys


def rr(t):
    return float(t.get('realized_r', t.get('realized_rr', 0.0)) or 0.0)


path = sys.argv[1] if len(sys.argv) > 1 else 'scratch/exp_target_structural_01_dev_results.json'
d = json.load(open(path))
trades = d['all_trades']

print('== LOSERS: context forensics ==')
for t in trades:
    if rr(t) >= 0:
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
    print(f"  {t.get('trade_id','?')[:44]:44s} {dts} {str(t.get('timeframe_set')):6s} "
          f"dir={str(t.get('directional_permission'))[-4:]:5s} realR={rr(t):+.3f} MFE={float(t.get('mfe_r',0) or 0):.2f} "
          f"MAE={float(t.get('mae_r',0) or 0):.2f} ctx={str(prov.get('htf_context','?'))[:12]:12s} "
          f"phase={str(prov.get('htf_phase','?'))[-12:]:12s} mtfEv={str(prov.get('mtf_structural_event','?'))[-14:]:14s} "
          f"kzAge={(f'{kz_age_days:.1f}d' if kz_age_days is not None else 'N/A'):>7s} "
          f"entry={str(prov.get('ltf_entry_reason','?'))[:30]}")

print()
print('== ALL: context/phase/event distributions ==')
from collections import Counter
ctx = Counter(str(t.get('metadata', {}).get('structural_provenance', {}).get('htf_context', '?')) for t in trades)
phase = Counter(str(t.get('metadata', {}).get('structural_provenance', {}).get('htf_phase', '?')) for t in trades)
ev = Counter(str(t.get('metadata', {}).get('structural_provenance', {}).get('mtf_structural_event', '?')) for t in trades)
em = Counter(str(t.get('metadata', {}).get('structural_provenance', {}).get('ltf_entry_reason', '?')) for t in trades)
for name, cnt in [('htf_context', ctx), ('htf_phase', phase), ('mtf_event', ev), ('entry_model', em)]:
    print(f'  {name}:')
    for k, v in cnt.most_common():
        rows = [t for t in trades if str(t.get('metadata', {}).get('structural_provenance', {}).get(
            {'htf_context': 'htf_context', 'htf_phase': 'htf_phase', 'mtf_event': 'mtf_structural_event',
             'entry_model': 'ltf_entry_reason'}[name], '?')) == k]
        net = sum(rr(r) for r in rows)
        print(f'    {k[:36]:36s} N={v:3d} netR={net:+.2f} E={net/v:+.3f}')
