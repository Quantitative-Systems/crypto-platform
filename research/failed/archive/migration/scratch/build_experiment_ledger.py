"""Consolidate experiment results into a comparison ledger vs a control file.

Usage: python3 scratch/build_experiment_ledger.py <control.json> <treatment1.json> [<treatment2.json> ...]
"""
import json
import sys


def rr(t):
    return float(t.get('realized_r', t.get('realized_rr', 0.0)) or 0.0)


def load_trades(path):
    d = json.load(open(path))
    return d['all_trades'], d.get('aggregate_performance', {})


def metrics(trades):
    n = len(trades)
    if n == 0:
        return dict(N=0)
    wins = [t for t in trades if rr(t) > 0]
    losses = [t for t in trades if rr(t) < 0]
    be = [t for t in trades if rr(t) == 0]
    net = sum(rr(t) for t in trades)
    wsum = sum(rr(t) for t in wins)
    lsum = abs(sum(rr(t) for t in losses))
    pf = (wsum / lsum) if lsum > 1e-9 else (float('inf') if wsum > 0 else 0.0)
    # max drawdown in R on chronological equity
    eq = 0.0
    peak = 0.0
    dd = 0.0
    for t in sorted(trades, key=lambda x: float(x.get('exit_timestamp', x.get('entry_timestamp', 0)) or 0)):
        eq += rr(t)
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    mfe = [float(t.get('mfe_r', 0) or 0) for t in trades]
    mae = [float(t.get('mae_r', 0) or 0) for t in trades]
    plrr = [float(t.get('raw_rr', 0) or 0) for t in trades]
    return dict(
        N=n, W=len(wins), L=len(losses), BE=len(be),
        WR=round(len(wins) / n * 100, 1),
        netR=round(net, 4), E=round(net / n, 4), PF=round(pf, 3),
        maxDD=round(abs(dd), 3),
        avgWin=round(wsum / len(wins), 3) if wins else 0.0,
        avgLoss=round(-lsum / len(losses), 3) if losses else 0.0,
        medMFE=round(sorted(mfe)[n // 2], 2), medMAE=round(sorted(mae)[n // 2], 2),
        avgPlanRR=round(sum(plrr) / n, 2),
        tgtHits=sum(1 for t in trades if t.get('exit_reason') == 'HTF_TP'),
    )


def fmt_row(name, m):
    if m.get('N', 0) == 0:
        return f"  {name:38s} N=0"
    return (f"  {name:38s} N={m['N']:3d} W={m['W']:3d} L={m['L']:3d} BE={m['BE']:3d} "
            f"WR={m['WR']:5.1f}% netR={m['netR']:+8.3f} E={m['E']:+.4f} PF={m['PF']:6.3f} "
            f"DD={m['maxDD']:6.3f} tgt={m['tgtHits']} avgWin={m['avgWin']:+.2f} avgLoss={m['avgLoss']:+.2f} "
            f"planRR={m['avgPlanRR']:.2f}")


control_path = sys.argv[1]
ct, _ = load_trades(control_path)
cm = metrics(ct)
print(f"CONTROL: {control_path}")
print(fmt_row('CONTROL', cm))
print()
for path in sys.argv[2:]:
    tt, agg = load_trades(path)
    tm = metrics(tt)
    print(f"TREATMENT: {path}")
    print(fmt_row('all', tm))
    ct_ids = {t['trade_id'] for t in ct}
    # delta on shared population + new/removed
    shared = [t for t in tt if t['trade_id'] in ct_ids]
    only_new = [t for t in tt if t['trade_id'] not in ct_ids]
    removed = [t for t in ct if t['trade_id'] not in {x['trade_id'] for x in tt}]
    # shared R delta
    ctrades = {t['trade_id']: rr(t) for t in ct}
    shared_delta = sum(rr(t) - ctrades.get(t['trade_id'], 0.0) for t in shared)
    print(fmt_row('shared population', metrics(shared)))
    print(fmt_row('new entries', metrics(only_new)))
    print(fmt_row('removed control entries', metrics(removed)))
    print(f"  {'shared-population R delta':38s} {shared_delta:+.4f}")
    print(f"  {'total R delta vs control':38s} {tm.get('netR', 0) - cm['netR']:+.4f}")
    # By asset / set / event breakdowns
    print('  -- by asset --')
    for a in ['BTC', 'ETH', 'SOL']:
        print(fmt_row(a, metrics([t for t in tt if t.get('symbol', '').startswith(a)])))
    print('  -- by set --')
    for s in ['SET_1', 'SET_2', 'SET_3', 'SET_4', 'SET_5']:
        print(fmt_row(s, metrics([t for t in tt if t.get('timeframe_set') == s])))
    print('  -- by mtf event --')
    evs = sorted(set(str(t.get('metadata', {}).get('structural_provenance', {}).get('mtf_structural_event', '?')) for t in tt))
    for e in evs:
        rows = [t for t in tt if str(t.get('metadata', {}).get('structural_provenance', {}).get('mtf_structural_event', '?')) == e]
        print(fmt_row(e, metrics(rows)))
    print()
