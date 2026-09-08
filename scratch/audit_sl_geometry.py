import json
import numpy as np
from collections import defaultdict

def rank_data(a):
    arr = np.array(a)
    sorter = np.argsort(arr)
    ranks = np.empty_like(sorter, dtype=float)
    ranks[sorter] = np.arange(len(arr), dtype=float)
    return ranks

def spearman_rho(x, y):
    rx = rank_data(x)
    ry = rank_data(y)
    return float(np.corrcoef(rx, ry)[0, 1])

def pearson_r(x, y):
    return float(np.corrcoef(x, y)[0, 1])

def run_audit():
    with open('scratch/canonical_35_trade_audit_ledger.json') as f:
        t35 = json.load(f)
    with open('scratch/canonical_anchor_2_dev_results.json') as f:
        a2 = json.load(f)

    a2_map = {t['trade_id']: t for t in a2['all_trades']}

    seen = set()
    clean = []
    for t in t35:
        tid = t['trade_id']
        if tid not in seen:
            seen.add(tid)
            t_full = dict(t)
            if tid in a2_map:
                t_full['trend_regime'] = a2_map[tid].get('trend_regime')
                t_full['volatility_regime'] = a2_map[tid].get('volatility_regime')
                t_full['htf_phase'] = a2_map[tid].get('metadata', {}).get('structural_provenance', {}).get('htf_phase')
                t_full['htf_target_provenance'] = a2_map[tid].get('metadata', {}).get('structural_provenance', {}).get('htf_target_provenance')
            
            # Counterfactual H1.1 on clean opportunity
            if t_full['realized_R'] > 0:
                t_full['h1_1_exit'] = t_full['exit_reason']
                t_full['h1_1_R'] = t_full['realized_R']
            elif t_full['MFE_R'] >= 1.0:
                t_full['h1_1_exit'] = 'LOCAL_TRAIL_LOCKED'
                t_full['h1_1_R'] = 0.0482
            else:
                t_full['h1_1_exit'] = t_full['exit_reason']
                t_full['h1_1_R'] = t_full['realized_R']
            
            # SL geometry calculations
            entry = t_full['entry_price']
            sl = t_full['initial_SL']
            risk_dist = abs(entry - sl)
            sl_dist_pct = (risk_dist / entry) * 100.0
            t_full['risk_dist'] = risk_dist
            t_full['sl_dist_pct'] = sl_dist_pct
            
            # Required 4R calculations
            req_4r_dist = 4.0 * risk_dist
            req_4r_pct = 4.0 * sl_dist_pct
            if t_full['direction'] == 'LONG':
                req_4r_price = entry + req_4r_dist
            else:
                req_4r_price = entry - req_4r_dist
            t_full['req_4r_dist'] = req_4r_dist
            t_full['req_4r_pct'] = req_4r_pct
            t_full['req_4r_price'] = req_4r_price
            
            # Ratio MFE to required 4R
            t_full['mfe_to_req_4r_pct'] = (t_full['MFE_R'] / 4.0) * 100.0
            t_full['mfe_to_planned_target_pct'] = (t_full['MFE_R'] / t_full['planned_RR']) * 100.0 if t_full['planned_RR'] > 0 else 0.0
            
            clean.append(t_full)

    # Output dictionary
    summary = {
        'total_trades': len(clean),
        'trades': clean,
        'bands': {},
        'correlations': {},
        'caps': {},
        'timeframes': {},
        'assets': {},
        'regimes': {}
    }

    # BANDS
    bands = [
        ("<2%", lambda s: s < 2.0),
        ("2–<3%", lambda s: 2.0 <= s < 3.0),
        ("3–<4%", lambda s: 3.0 <= s < 4.0),
        ("4–<5%", lambda s: 4.0 <= s < 5.0),
        ("5–<7.5%", lambda s: 5.0 <= s < 7.5),
        ("7.5–<10%", lambda s: 7.5 <= s < 10.0),
        (">=10%", lambda s: s >= 10.0),
    ]

    for bname, bfn in bands:
        btrades = [t for t in clean if bfn(t['sl_dist_pct'])]
        cnt = len(btrades)
        pct = cnt / len(clean) * 100.0
        if cnt > 0:
            wins = [t for t in btrades if t['realized_R'] > 0]
            losses = [t for t in btrades if t['realized_R'] < 0]
            net_r = float(sum(t['realized_R'] for t in btrades))
            exp_r = net_r / cnt
            mfes = [t['MFE_R'] for t in btrades]
            maes = [t['MAE_R'] for t in btrades]
            tgts = [t['planned_RR'] for t in btrades]
            mfe_tgts = [t['mfe_to_planned_target_pct'] for t in btrades]
            h1_rs = [t['h1_1_R'] for t in btrades]
            h1_net_r = float(sum(h1_rs))
            h1_exp_r = h1_net_r / cnt
            summary['bands'][bname] = {
                'count': cnt,
                'pct': pct,
                'wins': len(wins),
                'losses': len(losses),
                'h0_net_r': net_r,
                'h0_exp_r': exp_r,
                'h1_net_r': h1_net_r,
                'h1_exp_r': h1_exp_r,
                'mean_mfe': float(np.mean(mfes)),
                'median_mfe': float(np.median(mfes)),
                'mean_mae': float(np.mean(maes)),
                'median_mae': float(np.median(maes)),
                'mean_target_rr': float(np.mean(tgts)),
                'median_target_rr': float(np.median(tgts)),
                'mean_mfe_tgt_ratio': float(np.mean(mfe_tgts)),
                'median_mfe_tgt_ratio': float(np.median(mfe_tgts))
            }
        else:
            summary['bands'][bname] = {'count': 0, 'pct': 0.0}

    # CORRELATIONS
    sl_pcts = [t['sl_dist_pct'] for t in clean]
    mfes = [t['MFE_R'] for t in clean]
    maes = [t['MAE_R'] for t in clean]
    net_rs = [t['realized_R'] for t in clean]
    planned_rrs = [t['planned_RR'] for t in clean]
    mfe_tgt_ratios = [t['mfe_to_planned_target_pct'] for t in clean]

    summary['correlations'] = {
        'sl_vs_mfe': {'pearson': pearson_r(sl_pcts, mfes), 'spearman': spearman_rho(sl_pcts, mfes)},
        'sl_vs_realized_r': {'pearson': pearson_r(sl_pcts, net_rs), 'spearman': spearman_rho(sl_pcts, net_rs)},
        'sl_vs_planned_target': {'pearson': pearson_r(sl_pcts, planned_rrs), 'spearman': spearman_rho(sl_pcts, planned_rrs)},
        'sl_vs_mfe_target_ratio': {'pearson': pearson_r(sl_pcts, mfe_tgt_ratios), 'spearman': spearman_rho(sl_pcts, mfe_tgt_ratios)},
        'sl_vs_mae': {'pearson': pearson_r(sl_pcts, maes), 'spearman': spearman_rho(sl_pcts, maes)}
    }

    # CAPS
    caps = [2.0, 3.0, 4.0, 5.0, 7.5]
    total_wins = [t for t in clean if t['realized_R'] > 0]
    total_losses = [t for t in clean if t['realized_R'] < 0]

    for cap in caps:
        retained = [t for t in clean if t['sl_dist_pct'] <= cap]
        rejected = [t for t in clean if t['sl_dist_pct'] > cap]
        
        ret_wins = [t for t in retained if t['realized_R'] > 0]
        ret_losses = [t for t in retained if t['realized_R'] < 0]
        rej_wins = [t for t in rejected if t['realized_R'] > 0]
        rej_losses = [t for t in rejected if t['realized_R'] < 0]
        
        net_r = float(sum(t['realized_R'] for t in retained)) if retained else 0.0
        exp_r = net_r / len(retained) if retained else 0.0
        pos_sum = sum(t['realized_R'] for t in ret_wins)
        neg_sum = abs(sum(t['realized_R'] for t in ret_losses))
        pf = float(pos_sum / neg_sum) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)
        
        ret_mfes = [t['MFE_R'] for t in retained] if retained else [0.0]
        ret_tgts = [t['planned_RR'] for t in retained] if retained else [0.0]
        ret_ratios = [t['mfe_to_planned_target_pct'] for t in retained] if retained else [0.0]
        
        h1_retained_r = [t['h1_1_R'] for t in retained]
        h1_net_r = float(sum(h1_retained_r)) if retained else 0.0
        h1_exp_r = h1_net_r / len(retained) if retained else 0.0
        h1_pos_sum = sum(r for r in h1_retained_r if r > 0)
        h1_neg_sum = abs(sum(r for r in h1_retained_r if r < 0))
        h1_pf = float(h1_pos_sum / h1_neg_sum) if h1_neg_sum > 0 else 0.0

        summary['caps'][f"cap_{cap:.1f}%"] = {
            'cap_pct': cap,
            'retained_count': len(retained),
            'rejected_count': len(rejected),
            'retained_wins': len(ret_wins),
            'retained_losses': len(ret_losses),
            'rejected_wins': len(rej_wins),
            'rejected_losses': len(rej_losses),
            'rejected_win_ids': [t['trade_id'] for t in rej_wins],
            'h0_net_r': net_r,
            'h0_exp_r': exp_r,
            'h0_pf': pf,
            'h1_net_r': h1_net_r,
            'h1_exp_r': h1_exp_r,
            'h1_pf': h1_pf,
            'mean_mfe': float(np.mean(ret_mfes)),
            'median_mfe': float(np.median(ret_mfes)),
            'mean_target': float(np.mean(ret_tgts)),
            'median_target': float(np.median(ret_tgts)),
            'mean_mfe_target_ratio': float(np.mean(ret_ratios)),
            'median_mfe_target_ratio': float(np.median(ret_ratios))
        }

    # TIMEFRAMES
    for tf in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        tft = [t for t in clean if t['timeframe_set'] == tf]
        cnt = len(tft)
        if cnt > 0:
            sl_dists = [t['sl_dist_pct'] for t in tft]
            ge_10 = [t for t in tft if t['sl_dist_pct'] >= 10.0]
            ge_5 = [t for t in tft if t['sl_dist_pct'] >= 5.0]
            wins = [t for t in tft if t['realized_R'] > 0]
            losses = [t for t in tft if t['realized_R'] < 0]
            net_r = float(sum(t['realized_R'] for t in tft))
            exp_r = net_r / cnt
            tgts = [t['planned_RR'] for t in tft]
            mfes = [t['MFE_R'] for t in tft]
            ratios = [t['mfe_to_planned_target_pct'] for t in tft]
            summary['timeframes'][tf] = {
                'count': cnt,
                'wins': len(wins),
                'losses': len(losses),
                'h0_net_r': net_r,
                'h0_exp_r': exp_r,
                'sl_min': float(np.min(sl_dists)),
                'sl_25': float(np.percentile(sl_dists, 25)),
                'sl_median': float(np.median(sl_dists)),
                'sl_mean': float(np.mean(sl_dists)),
                'sl_75': float(np.percentile(sl_dists, 75)),
                'sl_max': float(np.max(sl_dists)),
                'sl_ge_10_count': len(ge_10),
                'sl_ge_5_count': len(ge_5),
                'mean_target': float(np.mean(tgts)),
                'median_target': float(np.median(tgts)),
                'mean_mfe': float(np.mean(mfes)),
                'median_mfe': float(np.median(mfes)),
                'mean_ratio': float(np.mean(ratios)),
                'median_ratio': float(np.median(ratios))
            }

    # ASSETS
    for asset in ["SOL", "BTC", "ETH"]:
        at = [t for t in clean if t['asset'] == asset]
        sls = [t['sl_dist_pct'] for t in at]
        r_list = [t['realized_R'] for t in at]
        summary['assets'][asset] = {
            'count': len(at),
            'wins': sum(1 for r in r_list if r > 0),
            'losses': sum(1 for r in r_list if r < 0),
            'net_r': float(sum(r_list)),
            'exp_r': float(np.mean(r_list)),
            'mean_sl': float(np.mean(sls)),
            'median_sl': float(np.median(sls)),
            'min_sl': float(np.min(sls)),
            'max_sl': float(np.max(sls))
        }

    with open('scratch/sl_geometry_forensics_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("Saved scratch/sl_geometry_forensics_summary.json successfully.")

if __name__ == '__main__':
    run_audit()
