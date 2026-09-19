import json
import numpy as np
from collections import defaultdict

def run_entry_audit():
    # Cache loaded data dicts: fn -> {open_ts: candle} and fn -> sorted_candles_list
    candle_dict = {}
    candle_list = {}

    def get_data(fn):
        if fn not in candle_dict:
            raw = json.load(open(fn))
            candle_list[fn] = raw
            candle_dict[fn] = {c[0]//1000: (i, c) for i, c in enumerate(raw)}
        return candle_list[fn], candle_dict[fn]

    with open('scratch/canonical_anchor_2_dev_results.json') as f:
        a2 = json.load(f)

    # Filter to 23 clean trades
    seen = set()
    clean = []
    for t in a2['all_trades']:
        tid = t['trade_id']
        if tid not in seen:
            seen.add(tid)
            clean.append(t)

    assert len(clean) == 23, f"Expected 23 clean trades, got {len(clean)}"

    results = []

    for idx, t in enumerate(clean):
        sp = t['metadata']['structural_provenance']
        sym = t['symbol'].replace('/', '')
        tf = t['timeframe_set']
        direction = t['direction']
        is_long = direction == 'LONG'
        mfe_r = t['mfe_r']
        mae_r = t['mae_r']
        net_r = t['net_r']
        entry_px = float(t['entry_price'])
        sl_px = float(t['initial_stop_price'])
        risk_dist = abs(entry_px - sl_px)
        sl_dist_pct = (risk_dist / entry_px) * 100.0
        planned_rr = float(t['raw_rr'])

        # Timeframe definitions
        if tf == 'SET_4':
            ltf_str = '15m'
            mtf_str = '1h'
            ltf_sec = 900
            mtf_sec = 3600
        elif tf == 'SET_3':
            ltf_str = '1h'
            mtf_str = '4h'
            ltf_sec = 3600
            mtf_sec = 14400
        else: # SET_2
            ltf_str = '4h'
            mtf_str = '1d'
            ltf_sec = 14400
            mtf_sec = 86400

        ltf_fn = f'market_data/cache/binance_{sym}_{ltf_str}.json'
        mtf_fn = f'market_data/cache/binance_{sym}_{mtf_str}.json'

        ltf_raw, ltf_lookup = get_data(ltf_fn)
        mtf_raw, mtf_lookup = get_data(mtf_fn)

        conf_ts = sp.get('ltf_confirmation_timestamp')
        entry_ts = t['entry_timestamp']
        retest_ts = sp.get('mtf_retest_timestamp')
        align_ts = sp.get('mtf_alignment_timestamp')

        # Locate LTF confirmation candle
        ltf_entry_idx, ltf_candle = ltf_lookup.get(conf_ts, (None, None))
        assert ltf_candle is not None, f"Could not find LTF candle for {t['trade_id']} at {conf_ts}"

        o = float(ltf_candle[1])
        h = float(ltf_candle[2])
        l = float(ltf_candle[3])
        c = float(ltf_candle[4])
        v = float(ltf_candle[5])

        c_range = h - l
        c_range_pct = (c_range / o) * 100.0 if o > 0 else 0.0
        body = abs(c - o)
        body_pct = (body / o) * 100.0 if o > 0 else 0.0
        body_ratio = body / c_range if c_range > 0 else 0.0

        if is_long:
            close_loc = (c - l) / c_range if c_range > 0 else 0.5
            dir_aligned = (c > o)
        else:
            close_loc = (h - c) / c_range if c_range > 0 else 0.5
            dir_aligned = (c < o)

        # Prior 10 LTF candles range and body
        prior_ranges = []
        prior_bodies = []
        prior_lows = []
        prior_highs = []
        for p_idx in range(max(0, ltf_entry_idx - 10), ltf_entry_idx):
            pc = ltf_raw[p_idx]
            po, ph, pl, pclose = float(pc[1]), float(pc[2]), float(pc[3]), float(pc[4])
            prior_ranges.append(ph - pl)
            prior_bodies.append(abs(pclose - po))
            prior_lows.append(pl)
            prior_highs.append(ph)

        mean_prior_range = np.mean(prior_ranges) if prior_ranges else c_range
        rel_range = c_range / mean_prior_range if mean_prior_range > 0 else 1.0
        mean_prior_body = np.mean(prior_bodies) if prior_bodies else body
        rel_body = body / mean_prior_body if mean_prior_body > 0 else 1.0

        # Liquidity Sweep Forensics
        # Prior 10 lowest low (for long) or highest high (for short) before the trigger bar
        if is_long:
            prior_sweep_ref = min(prior_lows) if prior_lows else l
            sweep_depth = max(0.0, prior_sweep_ref - l)
            sweep_depth_pct = (sweep_depth / prior_sweep_ref) * 100.0 if prior_sweep_ref > 0 else 0.0
            sweep_dist_to_entry = abs(c - l)
        else:
            prior_sweep_ref = max(prior_highs) if prior_highs else h
            sweep_depth = max(0.0, h - prior_sweep_ref)
            sweep_depth_pct = (sweep_depth / prior_sweep_ref) * 100.0 if prior_sweep_ref > 0 else 0.0
            sweep_dist_to_entry = abs(h - c)

        sweep_dist_to_entry_pct = (sweep_dist_to_entry / c) * 100.0 if c > 0 else 0.0

        # Subsequent 3 LTF bars behavior
        subseq_adverse = []
        subseq_favorable = []
        for s_idx in range(ltf_entry_idx + 1, min(len(ltf_raw), ltf_entry_idx + 4)):
            sc = ltf_raw[s_idx]
            sh, sl_val = float(sc[2]), float(sc[3])
            if is_long:
                adv = max(0.0, entry_px - sl_val)
                fav = max(0.0, sh - entry_px)
            else:
                adv = max(0.0, sh - entry_px)
                fav = max(0.0, entry_px - sl_val)
            subseq_adverse.append(adv / risk_dist if risk_dist > 0 else 0.0)
            subseq_favorable.append(fav / risk_dist if risk_dist > 0 else 0.0)

        max_adv_3bar = max(subseq_adverse) if subseq_adverse else 0.0
        max_fav_3bar = max(subseq_favorable) if subseq_favorable else 0.0

        # Check immediate stall / reversal: did candle +1 close adverse to entry?
        if ltf_entry_idx + 1 < len(ltf_raw):
            c1 = ltf_raw[ltf_entry_idx + 1]
            c1_close = float(c1[4])
            c1_adverse_close = (c1_close < entry_px) if is_long else (c1_close > entry_px)
        else:
            c1_adverse_close = False

        # MTF Context & Timing
        sec_since_align = conf_ts - align_ts if align_ts else 0
        mtf_bars_since_align = sec_since_align / mtf_sec if mtf_sec > 0 else 0.0

        sec_since_retest = conf_ts - retest_ts if retest_ts else 0
        mtf_bars_since_retest = sec_since_retest / mtf_sec if mtf_sec > 0 else 0.0

        # Find MTF candle corresponding to conf_ts
        # In MTF, candle open timestamp is (conf_ts // mtf_sec) * mtf_sec
        mtf_open_ts = (conf_ts // mtf_sec) * mtf_sec
        mtf_cand_idx, mtf_cand = mtf_lookup.get(mtf_open_ts, (None, None))
        if mtf_cand:
            mtf_o, mtf_h, mtf_l, mtf_c = float(mtf_cand[1]), float(mtf_cand[2]), float(mtf_cand[3]), float(mtf_cand[4])
            mtf_range = mtf_h - mtf_l
            mtf_body = abs(mtf_c - mtf_o)
            mtf_body_ratio = mtf_body / mtf_range if mtf_range > 0 else 0.0
            if is_long:
                mtf_dir_aligned = (mtf_c > mtf_o)
                mtf_pos_in_range = (c - mtf_l) / mtf_range if mtf_range > 0 else 0.5
            else:
                mtf_dir_aligned = (mtf_c < mtf_o)
                mtf_pos_in_range = (mtf_h - c) / mtf_range if mtf_range > 0 else 0.5
        else:
            mtf_body_ratio = 0.0
            mtf_dir_aligned = False
            mtf_pos_in_range = 0.5

        # Group classification
        group = 'A' if mfe_r < 0.5 else 'B'
        is_winner = net_r > 0

        res = {
            'idx': idx + 1,
            'trade_id': t['trade_id'],
            'symbol': t['symbol'],
            'timeframe_set': tf,
            'direction': direction,
            'group': group,
            'is_winner': is_winner,
            'mfe_r': mfe_r,
            'mae_r': mae_r,
            'net_r': net_r,
            'entry_px': entry_px,
            'sl_px': sl_px,
            'sl_dist_pct': sl_dist_pct,
            'planned_rr': planned_rr,
            'ltf_entry_reason': sp.get('ltf_entry_reason'),
            'conf_ts': conf_ts,
            'entry_ts': entry_ts,
            # Displacement features
            'c_range': c_range,
            'c_range_pct': c_range_pct,
            'body_size': body,
            'body_size_pct': body_pct,
            'body_ratio': body_ratio,
            'rel_range': rel_range,
            'rel_body': rel_body,
            'close_loc': close_loc,
            'dir_aligned': dir_aligned,
            # Sweep features
            'sweep_depth': sweep_depth,
            'sweep_depth_pct': sweep_depth_pct,
            'sweep_dist_to_entry_pct': sweep_dist_to_entry_pct,
            # Immediate reaction
            'max_adv_3bar': max_adv_3bar,
            'max_fav_3bar': max_fav_3bar,
            'c1_adverse_close': c1_adverse_close,
            # MTF Timing & Momentum
            'sec_since_align': sec_since_align,
            'mtf_bars_since_align': mtf_bars_since_align,
            'sec_since_retest': sec_since_retest,
            'mtf_bars_since_retest': mtf_bars_since_retest,
            'mtf_body_ratio': mtf_body_ratio,
            'mtf_dir_aligned': mtf_dir_aligned,
            'mtf_pos_in_range': mtf_pos_in_range,
            'mtf_keyzone_id': sp.get('mtf_keyzone_id')
        }
        results.append(res)

    print("\n" + "="*80)
    print("PHASE 1: IMMEDIATE FAILURE (GROUP A) VS MEANINGFUL EXCURSION (GROUP B)")
    print("="*80)
    for gname in ['A', 'B']:
        gtrades = [r for r in results if r['group'] == gname]
        wins = [r for r in gtrades if r['is_winner']]
        losses = [r for r in gtrades if not r['is_winner']]
        net_r = sum(r['net_r'] for r in gtrades)
        exp_r = net_r / len(gtrades)
        mfes = [r['mfe_r'] for r in gtrades]
        maes = [r['mae_r'] for r in gtrades]
        sls = [r['sl_dist_pct'] for r in gtrades]
        tgts = [r['planned_rr'] for r in gtrades]
        print(f"\nGROUP {gname} (N={len(gtrades)}): Wins={len(wins)}, Losses={len(losses)}")
        print(f"  Net R: {net_r:+.4f}R | Expectancy: {exp_r:+.4f}R")
        print(f"  MFE: Median={np.median(mfes):.2f}R | Mean={np.mean(mfes):.2f}R | Min={np.min(mfes):.2f}R | Max={np.max(mfes):.2f}R")
        print(f"  MAE: Median={np.median(maes):.2f}R | Mean={np.mean(maes):.2f}R | Min={np.min(maes):.2f}R | Max={np.max(maes):.2f}R")
        print(f"  SL%: Median={np.median(sls):.2f}% | Mean={np.mean(sls):.2f}% | Range=[{np.min(sls):.2f}%, {np.max(sls):.2f}%]")
        print(f"  Target RR: Median={np.median(tgts):.2f}R | Mean={np.mean(tgts):.2f}R")

    print("\n" + "="*80)
    print("PHASE 2 & 6: DISPLACEMENT FEATURES COMPARISON (GROUP A VS GROUP B)")
    print("="*80)
    features = [
        ('Body/Range Ratio', 'body_ratio', '{:.3f}'),
        ('Candle Range %', 'c_range_pct', '{:.2f}%'),
        ('Body Size %', 'body_size_pct', '{:.2f}%'),
        ('Relative Range (vs 10 prior)', 'rel_range', '{:.2f}x'),
        ('Relative Body (vs 10 prior)', 'rel_body', '{:.2f}x'),
        ('Close Location in Candle', 'close_loc', '{:.3f}'),
        ('Sweep Depth %', 'sweep_depth_pct', '{:.2f}%'),
        ('Sweep-to-Entry Dist %', 'sweep_dist_to_entry_pct', '{:.2f}%'),
        ('MTF Bars Since Align', 'mtf_bars_since_align', '{:.2f}'),
        ('MTF Bars Since Retest', 'mtf_bars_since_retest', '{:.2f}'),
        ('3-Bar Max Adverse R', 'max_adv_3bar', '{:.2f}R'),
        ('3-Bar Max Favorable R', 'max_fav_3bar', '{:.2f}R')
    ]

    for fname, fkey, fmt in features:
        vals_a = [r[fkey] for r in results if r['group'] == 'A']
        vals_b = [r[fkey] for r in results if r['group'] == 'B']
        vals_w = [r[fkey] for r in results if r['is_winner']]
        print(f"\nFeature: {fname}")
        print(f"  Group A (<0.5R, N=10):  Median={fmt.format(np.median(vals_a))} | Mean={fmt.format(np.mean(vals_a))} | Range=[{fmt.format(np.min(vals_a))}, {fmt.format(np.max(vals_a))}]")
        print(f"  Group B (>=0.5R, N=13): Median={fmt.format(np.median(vals_b))} | Mean={fmt.format(np.mean(vals_b))} | Range=[{fmt.format(np.min(vals_b))}, {fmt.format(np.max(vals_b))}]")
        print(f"  Winners (N=2):          Values=[{', '.join(fmt.format(v) for v in vals_w)}]")

    # Check discrete boolean features
    print("\nDiscrete Features:")
    for bfeat, bkey in [('Candle 1 Adverse Close', 'c1_adverse_close'), ('MTF Dir Aligned', 'mtf_dir_aligned')]:
        a_cnt = sum(1 for r in results if r['group'] == 'A' and r[bkey])
        b_cnt = sum(1 for r in results if r['group'] == 'B' and r[bkey])
        print(f"  {bfeat}: Group A={a_cnt}/10 ({a_cnt*10}%) | Group B={b_cnt}/13 ({b_cnt/13*100:.1f}%)")

    # Save summary json
    with open('scratch/entry_quality_forensics_summary.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nSaved scratch/entry_quality_forensics_summary.json successfully.")

if __name__ == '__main__':
    run_entry_audit()
