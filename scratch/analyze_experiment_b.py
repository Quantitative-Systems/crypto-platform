import os
import sys
import json
import numpy as np
from typing import Dict, Any, List

def load_results(path: str) -> Dict[str, Any]:
    with open(path, "r") as fp:
        return json.load(fp)

def analyze_population(data: Dict[str, Any], label: str) -> Dict[str, Any]:
    trades = data.get("all_trades", [])
    stream_res = data.get("stream_results", [])
    agg = data.get("aggregate_performance", {})
    
    # Funnel
    total_candidates = sum(len(s.get("all_candidates", [])) for s in stream_res)
    risk_gate_candidates = 0
    rr_rejections = 0
    approved = 0
    for s in stream_res:
        for c in s.get("all_candidates", []):
            st = str(c.get("state", ""))
            rej = str(c.get("rejection_reason", ""))
            stages = c.get("stages_reached", [])
            if "RISK_GATE" in stages or "RISK_GATE" in st or "RR" in rej or c.get("planned_rr") is not None or "ENTERED" in st or "CLOSED" in st:
                risk_gate_candidates += 1
            if "REJECT_RR_BELOW_4R" in rej or "BELOW_4R" in rej:
                rr_rejections += 1
            if "APPROVED" in st or "ENTERED" in st or "CLOSED" in st:
                approved += 1

    executed_trades = len(trades)
    
    # Performance
    wins = [t for t in trades if t.get("net_r", t.get("realized_rr", 0.0)) > 0.0]
    losses = [t for t in trades if t.get("net_r", t.get("realized_rr", 0.0)) < 0.0]
    bes = [t for t in trades if abs(t.get("net_r", t.get("realized_rr", 0.0))) < 1e-6]
    
    gross_r = sum(t.get("gross_r", 0.0) for t in trades)
    friction_r = sum((t.get("fees_r", 0.0) + t.get("slippage_r", 0.0)) for t in trades)
    net_r = sum(t.get("net_r", t.get("realized_rr", 0.0)) for t in trades)
    expectancy = net_r / executed_trades if executed_trades > 0 else 0.0
    
    gross_wins = sum(t.get("net_r", t.get("realized_rr", 0.0)) for t in wins)
    gross_losses = abs(sum(t.get("net_r", t.get("realized_rr", 0.0)) for t in losses))
    pf = (gross_wins / gross_losses) if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)
    
    # Drawdown & consecutive losses
    cum_r = 0.0
    peak_r = 0.0
    max_dd = 0.0
    cur_consec_losses = 0
    max_consec_losses = 0
    for t in trades:
        r = t.get("net_r", t.get("realized_rr", 0.0))
        cum_r += r
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd:
            max_dd = dd
        if r < 0.0:
            cur_consec_losses += 1
            if cur_consec_losses > max_consec_losses:
                max_consec_losses = cur_consec_losses
        else:
            cur_consec_losses = 0

    # Excursion
    mfes = [t.get("mfe_r", 0.0) for t in trades]
    maes = [t.get("mae_r", 0.0) for t in trades]
    
    avg_mfe = float(np.mean(mfes)) if mfes else 0.0
    med_mfe = float(np.median(mfes)) if mfes else 0.0
    avg_mae = float(np.mean(maes)) if maes else 0.0
    med_mae = float(np.median(maes)) if maes else 0.0
    
    mfe_ge_1r = sum(1 for m in mfes if m >= 1.0)
    mfe_ge_2r = sum(1 for m in mfes if m >= 2.0)
    mfe_ge_3r = sum(1 for m in mfes if m >= 3.0)
    mfe_ge_4r = sum(1 for m in mfes if m >= 4.0)
    mfe_ge_5r = sum(1 for m in mfes if m >= 5.0)
    
    # Target interaction
    target_hits = sum(1 for t in trades if "TARGET" in str(t.get("exit_reason", "")).upper() or "TP" in str(t.get("exit_reason", "")).upper())
    hit_rate = target_hits / executed_trades if executed_trades > 0 else 0.0
    
    reach_cond_1r = target_hits / mfe_ge_1r if mfe_ge_1r > 0 else 0.0
    reach_cond_2r = target_hits / mfe_ge_2r if mfe_ge_2r > 0 else 0.0
    reach_cond_3r = target_hits / mfe_ge_3r if mfe_ge_3r > 0 else 0.0
    
    # Planned RR & target distance
    planned_rrs = [t.get("raw_rr", t.get("planned_rr", 0.0)) for t in trades if t.get("raw_rr") or t.get("planned_rr")]
    avg_planned_rr = float(np.mean(planned_rrs)) if planned_rrs else 0.0
    med_planned_rr = float(np.median(planned_rrs)) if planned_rrs else 0.0
    
    # Target distance in R
    target_dist_r = []
    for t in trades:
        entry = t.get("entry_price", 0.0)
        target = t.get("target_price", 0.0)
        stop = t.get("stop_price", t.get("sl_price", 0.0))
        risk = abs(entry - stop)
        if risk > 0:
            target_dist_r.append(abs(target - entry) / risk)
    avg_target_dist_r = float(np.mean(target_dist_r)) if target_dist_r else 0.0
    med_target_dist_r = float(np.median(target_dist_r)) if target_dist_r else 0.0

    # Exit attribution
    exit_counts = {}
    exit_rs = {}
    for t in trades:
        reason = t.get("exit_reason", "UNKNOWN")
        r = t.get("net_r", t.get("realized_rr", 0.0))
        exit_counts[reason] = exit_counts.get(reason, 0) + 1
        exit_rs[reason] = exit_rs.get(reason, 0.0) + r

    # Monetization failure diagnostic: MFE >= 2R/3R/4R/5R but realized R < 0
    mfe2_loss = [t for t in trades if t.get("mfe_r", 0.0) >= 2.0 and t.get("net_r", t.get("realized_rr", 0.0)) < 0.0]
    mfe3_loss = [t for t in trades if t.get("mfe_r", 0.0) >= 3.0 and t.get("net_r", t.get("realized_rr", 0.0)) < 0.0]
    mfe4_loss = [t for t in trades if t.get("mfe_r", 0.0) >= 4.0 and t.get("net_r", t.get("realized_rr", 0.0)) < 0.0]
    mfe5_loss = [t for t in trades if t.get("mfe_r", 0.0) >= 5.0 and t.get("net_r", t.get("realized_rr", 0.0)) < 0.0]
    
    # Asset breakdown
    assets = ["BTC", "ETH", "SOL"]
    asset_data = {}
    for a in assets:
        a_trades = [t for t in trades if a in t.get("stream_id", "") or a in t.get("symbol", "")]
        a_n = len(a_trades)
        a_wins = len([t for t in a_trades if t.get("net_r", t.get("realized_rr", 0.0)) > 0.0])
        a_net_r = sum(t.get("net_r", t.get("realized_rr", 0.0)) for t in a_trades)
        a_exp = a_net_r / a_n if a_n > 0 else 0.0
        asset_data[a] = {
            "n": a_n, "wins": a_wins, "losses": a_n - a_wins,
            "win_rate": (a_wins / a_n * 100.0) if a_n > 0 else 0.0,
            "net_r": a_net_r, "expectancy": a_exp
        }
        
    # Timeframe set breakdown
    tf_sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]
    tf_data = {}
    for tf in tf_sets:
        tf_trades = [t for t in trades if tf in t.get("stream_id", "")]
        tf_n = len(tf_trades)
        tf_wins = len([t for t in tf_trades if t.get("net_r", t.get("realized_rr", 0.0)) > 0.0])
        tf_net_r = sum(t.get("net_r", t.get("realized_rr", 0.0)) for t in tf_trades)
        tf_exp = tf_net_r / tf_n if tf_n > 0 else 0.0
        tf_data[tf] = {
            "n": tf_n, "wins": tf_wins, "losses": tf_n - tf_wins,
            "net_r": tf_net_r, "expectancy": tf_exp
        }

    # Provenance
    prov_counts = {}
    prov_rs = {}
    prov_mfes = {}
    for t in trades:
        meta = t.get("metadata", {})
        sp = meta.get("structural_provenance", {}) if isinstance(meta, dict) else {}
        src = sp.get("htf_target_provenance", t.get("target_source", t.get("destination_type", "UNKNOWN")))
        r = t.get("net_r", t.get("realized_rr", 0.0))
        mfe = t.get("mfe_r", 0.0)
        prov_counts[src] = prov_counts.get(src, 0) + 1
        prov_rs[src] = prov_rs.get(src, 0.0) + r
        if src not in prov_mfes:
            prov_mfes[src] = []
        prov_mfes[src].append(mfe)

    return {
        "label": label,
        "funnel": {
            "total_candidates": total_candidates,
            "risk_gate_candidates": risk_gate_candidates,
            "rr_rejections": rr_rejections,
            "approved": approved,
            "executed_trades": executed_trades
        },
        "performance": {
            "n": executed_trades,
            "wins": len(wins),
            "losses": len(losses),
            "breakevens": len(bes),
            "win_rate_pct": (len(wins) / executed_trades * 100.0) if executed_trades > 0 else 0.0,
            "gross_r": gross_r,
            "friction_r": friction_r,
            "net_r": net_r,
            "expectancy": expectancy,
            "profit_factor": pf,
            "max_drawdown_r": max_dd,
            "max_consecutive_losses": max_consec_losses
        },
        "excursion": {
            "avg_mfe_r": avg_mfe,
            "med_mfe_r": med_mfe,
            "avg_mae_r": avg_mae,
            "med_mae_r": med_mae,
            "mfe_ge_1r": mfe_ge_1r,
            "mfe_ge_2r": mfe_ge_2r,
            "mfe_ge_3r": mfe_ge_3r,
            "mfe_ge_4r": mfe_ge_4r,
            "mfe_ge_5r": mfe_ge_5r
        },
        "target_interaction": {
            "target_reach_count": target_hits,
            "target_reach_rate_pct": hit_rate * 100.0,
            "reach_cond_1r_pct": reach_cond_1r * 100.0,
            "reach_cond_2r_pct": reach_cond_2r * 100.0,
            "reach_cond_3r_pct": reach_cond_3r * 100.0,
            "avg_planned_rr": avg_planned_rr,
            "med_planned_rr": med_planned_rr,
            "avg_target_dist_r": avg_target_dist_r,
            "med_target_dist_r": med_target_dist_r
        },
        "exit_attribution": {
            "counts": exit_counts,
            "realized_r": exit_rs
        },
        "monetization_failures": {
            "mfe2_loss_count": len(mfe2_loss),
            "mfe3_loss_count": len(mfe3_loss),
            "mfe4_loss_count": len(mfe4_loss),
            "mfe5_loss_count": len(mfe5_loss),
            "trades": [
                {
                    "trade_id": t.get("trade_id", 0),
                    "stream_id": t.get("stream_id", ""),
                    "mfe_r": t.get("mfe_r", 0.0),
                    "realized_r": t.get("net_r", t.get("realized_rr", 0.0)),
                    "exit_reason": t.get("exit_reason", "")
                }
                for t in mfe2_loss
            ]
        },
        "asset_attribution": asset_data,
        "timeframe_attribution": tf_data,
        "target_provenance": {
            "counts": prov_counts,
            "realized_r": prov_rs,
            "avg_mfe": {k: float(np.mean(v)) for k, v in prov_mfes.items()}
        }
    }

if __name__ == "__main__":
    h0_path = sys.argv[1] if len(sys.argv) > 1 else "/home/mrcn2/crypto-platform/scratch/canonical_h0_backtest_dev.json"
    exp_path = sys.argv[2] if len(sys.argv) > 2 else "/home/mrcn2/crypto-platform/scratch/exp_target_structural_01_pure_dev.json"
    
    if os.path.exists(h0_path) and os.path.exists(exp_path):
        h0_data = load_results(h0_path)
        exp_data = load_results(exp_path)
        
        rep_h0 = analyze_population(h0_data, "Corrected Canonical H0 (Control)")
        rep_exp = analyze_population(exp_data, "EXP_TARGET_STRUCTURAL_01 (Treatment)")
        
        out = {
            "h0": rep_h0,
            "exp": rep_exp
        }
        with open("/home/mrcn2/crypto-platform/scratch/experiment_b_comparison.json", "w") as fp:
            json.dump(out, fp, indent=2)
        print("Comparison analysis saved to scratch/experiment_b_comparison.json")
