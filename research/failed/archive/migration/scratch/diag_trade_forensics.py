"""Diagnostic: trade-by-trade forensics for a dev-results JSON file."""
import json
import sys


def rr(t):
    return float(t.get('realized_r', t.get('realized_rr', 0.0)) or 0.0)


path = sys.argv[1] if len(sys.argv) > 1 else 'scratch/exp_target_structural_01_dev_results.json'
d = json.load(open(path))
trades = d['all_trades']
print('N =', len(trades))
hdr = f"{'id':40s} {'asset':5s} {'set':6s} {'dir':5s} {'planRR':>7s} {'realR':>8s} {'MFE':>6s} {'MAE':>6s} {'exit':30s} {'tgtType':28s}"
print(hdr)
print('-' * len(hdr))
for t in trades:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    tgt = prov.get('htf_target_provenance', '?') if isinstance(prov, dict) else '?'
    print(f"{str(t.get('trade_id','?'))[:40]:40s} {str(t.get('symbol','?'))[:5]:5s} "
          f"{str(t.get('timeframe_set','?')):6s} {str(t.get('directional_permission','?'))[-4:]:5s} "
          f"{float(t.get('raw_rr',0) or 0):7.2f} {rr(t):8.3f} "
          f"{float(t.get('mfe_r',0) or 0):6.2f} {float(t.get('mae_r',0) or 0):6.2f} "
          f"{str(t.get('exit_reason','?'))[:30]:30s} {str(tgt)[:28]:28s}")


# Aggregate by dimensions
def agg(rows, label):
    n = len(rows)
    if n == 0:
        print(f"  {label:30s} N=0")
        return
    wins = [r for r in rows if rr(r) > 0]
    losses = [r for r in rows if rr(r) < 0]
    net = sum(rr(r) for r in rows)
    wr = len(wins) / n * 100
    wsum = sum(rr(r) for r in wins)
    lsum = abs(sum(rr(r) for r in losses))
    pf = (wsum / lsum) if lsum > 0 else float('inf') if wsum > 0 else 0.0
    mfes = sorted(float(r.get('mfe_r', 0) or 0) for r in rows)
    print(f"  {label:30s} N={n:3d} W={len(wins):3d} L={len(losses):3d} netR={net:+8.2f} WR={wr:5.1f}% "
          f"PF={pf:5.2f} E={net/n:+.3f} medMFE={mfes[len(mfes)//2]:.2f}")


print('\n== By asset ==')
for a in ['BTC', 'ETH', 'SOL']:
    agg([t for t in trades if t.get('symbol', '').startswith(a)], a)
print('== By set ==')
for s in ['SET_1', 'SET_2', 'SET_3', 'SET_4', 'SET_5']:
    agg([t for t in trades if t.get('timeframe_set') == s], s)
print('== By direction ==')
for dd, lbl in [('LONG', 'long'), ('SHORT', 'short')]:
    agg([t for t in trades if dd in str(t.get('directional_permission', ''))], lbl)
print('== By exit reason ==')
for k in sorted(set(str(t.get('exit_reason', '?')) for t in trades)):
    agg([t for t in trades if str(t.get('exit_reason')) == k], k)
print('== By target type ==')
for t in trades:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    t['_tgt'] = str(prov.get('htf_target_provenance', '?')) if isinstance(prov, dict) else '?'
for k in sorted(set(t.get('_tgt', '?') for t in trades)):
    agg([t for t in trades if t.get('_tgt', '?') == k], k)
print('== By entry model ==')
for t in trades:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    t['_em'] = str(prov.get('entry_model', prov.get('ltf_entry_model', '?')))[:24] if isinstance(prov, dict) else '?'
for k in sorted(set(t.get('_em', '?') for t in trades)):
    agg([t for t in trades if t.get('_em', '?') == k], k)
print('== MFE histogram (all trades) ==')
buckets = [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 4), (4, 100)]
for lo, hi in buckets:
    n = sum(1 for t in trades if lo <= float(t.get('mfe_r', 0) or 0) < hi)
    print(f"  MFE [{lo:>4}, {hi:>4}): {n}")
lt = [t for t in trades if rr(t) < 0]
print(f'== Losing trades (N={len(lt)}) MFE histogram ==')
for lo, hi in buckets:
    n = sum(1 for t in lt if lo <= float(t.get('mfe_r', 0) or 0) < hi)
    print(f"  MFE [{lo:>4}, {hi:>4}): {n}")
wt = [t for t in trades if rr(t) > 0]
print(f'== Winning trades (N={len(wt)}) ==')
for t in wt:
    prov = t.get('metadata', {}).get('structural_provenance', {})
    print(f"  {str(t.get('trade_id','?'))[:44]:44s} realR={rr(t):+.2f} MFE={float(t.get('mfe_r',0) or 0):.2f} "
          f"exit={str(t.get('exit_reason'))[:24]:24s} tgt={str(prov.get('htf_target_provenance','?'))[:24]}")
