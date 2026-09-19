import json
import os
import numpy as np

def load_trades(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        data = json.load(f)
    return data.get("all_trades", [])

def compute_metrics(trades, label):
    if trades is None:
        return None
    
    n = len(trades)
    if n == 0:
        return {"n": 0}
        
    wins = [t for t in trades if t.get("net_r", 0) > 0.05]
    losses = [t for t in trades if t.get("net_r", 0) < -0.05]
    breakevens = [t for t in trades if -0.05 <= t.get("net_r", 0) <= 0.05]
    
    n_wins = len(wins)
    n_losses = len(losses)
    n_be = len(breakevens)
    
    win_rate = (n_wins / n) * 100.0
    
    net_r_list = [t.get("net_r", 0.0) for t in trades]
    gross_r_list = [t.get("gross_r", 0.0) for t in trades]
    friction_r_list = [t.get("fees_r", 0.0) + t.get("slippage_r", 0.0) for t in trades]
    mfe_r_list = [t.get("mfe_r", 0.0) for t in trades]
    mae_r_list = [t.get("mae_r", 0.0) for t in trades]
    
    total_net_r = sum(net_r_list)
    total_gross_r = sum(gross_r_list)
    total_friction_r = sum(friction_r_list)
    expectancy = total_net_r / n
    
    pos_r = sum([r for r in net_r_list if r > 0])
    neg_r = abs(sum([r for r in net_r_list if r < 0]))
    pf = (pos_r / neg_r) if neg_r > 0 else (999.0 if pos_r > 0 else 0.0)
    
    # Max DD and max consecutive losses
    cum_r = 0.0
    peak_r = 0.0
    max_dd = 0.0
    consec_losses = 0
    max_consec_losses = 0
    
    for r in net_r_list:
        cum_r += r
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd:
            max_dd = dd
        if r < -0.05:
            consec_losses += 1
            if consec_losses > max_consec_losses:
                max_consec_losses = consec_losses
        else:
            consec_losses = 0
            
    # Monetization ratios
    retention_ratios = []
    for t in trades:
        mfe = t.get("mfe_r", 0.0)
        net_r = t.get("net_r", 0.0)
        if mfe > 0.0:
            retention_ratios.append(net_r / mfe)
            
    avg_retention = float(np.mean(retention_ratios)) if retention_ratios else 0.0
    med_retention = float(np.median(retention_ratios)) if retention_ratios else 0.0
    
    # Conditional realized R by MFE threshold
    def cond_avg_net_r(th):
        sub = [t.get("net_r", 0.0) for t in trades if t.get("mfe_r", 0.0) >= th]
        return float(np.mean(sub)) if sub else 0.0
        
    # Exit attribution
    exit_counts = {}
    exit_realized = {}
    for t in trades:
        reason = t.get("exit_reason", "UNKNOWN")
        exit_counts[reason] = exit_counts.get(reason, 0) + 1
        exit_realized[reason] = exit_realized.get(reason, 0.0) + t.get("net_r", 0.0)
        
    # Asset attribution
    asset_res = {}
    for asset in ["BTC", "ETH", "SOL"]:
        sub_t = [t for t in trades if asset in t.get("symbol", "")]
        n_a = len(sub_t)
        sub_net = sum([t.get("net_r", 0.0) for t in sub_t])
        sub_wins = len([t for t in sub_t if t.get("net_r", 0.0) > 0.05])
        asset_res[asset] = {
            "n": n_a,
            "wins": sub_wins,
            "win_rate": (sub_wins / n_a * 100.0) if n_a > 0 else 0.0,
            "net_r": sub_net,
            "expectancy": (sub_net / n_a) if n_a > 0 else 0.0
        }
        
    # Timeframe set attribution
    tf_res = {}
    for s_idx in range(1, 6):
        set_name = f"SET_{s_idx}"
        sub_t = [t for t in trades if set_name in t.get("stream_id", "") or set_name in t.get("timeframe_set", "")]
        n_s = len(sub_t)
        sub_net = sum([t.get("net_r", 0.0) for t in sub_t])
        sub_wins = len([t for t in sub_t if t.get("net_r", 0.0) > 0.05])
        tf_res[set_name] = {
            "n": n_s,
            "wins": sub_wins,
            "win_rate": (sub_wins / n_s * 100.0) if n_s > 0 else 0.0,
            "net_r": sub_net,
            "expectancy": (sub_net / n_s) if n_s > 0 else 0.0
        }

    return {
        "label": label,
        "n": n,
        "wins": n_wins,
        "losses": n_losses,
        "breakevens": n_be,
        "win_rate_pct": win_rate,
        "gross_r": total_gross_r,
        "friction_r": total_friction_r,
        "net_r": total_net_r,
        "expectancy": expectancy,
        "profit_factor": pf,
        "max_drawdown_r": max_dd,
        "max_consecutive_losses": max_consec_losses,
        "avg_mfe": float(np.mean(mfe_r_list)) if mfe_r_list else 0.0,
        "med_mfe": float(np.median(mfe_r_list)) if mfe_r_list else 0.0,
        "avg_mae": float(np.mean(mae_r_list)) if mae_r_list else 0.0,
        "med_mae": float(np.median(mae_r_list)) if mae_r_list else 0.0,
        "avg_retention": avg_retention,
        "med_retention": med_retention,
        "cond_2r_net_r": cond_avg_net_r(2.0),
        "cond_3r_net_r": cond_avg_net_r(3.0),
        "cond_4r_net_r": cond_avg_net_r(4.0),
        "cond_5r_net_r": cond_avg_net_r(5.0),
        "exit_counts": exit_counts,
        "exit_realized": exit_realized,
        "asset_attribution": asset_res,
        "tf_attribution": tf_res,
        "retention_ratios": retention_ratios
    }

def main():
    files = {
        "H0": ("scratch/canonical_h0_backtest_dev.json", "H0 (Control: Pure MTF Trailing)"),
        "C1": ("scratch/exp_c1_dev.json", "C1 (Protective Stop @ +1.5R)"),
        "C2": ("scratch/exp_c2_dev.json", "C2 (Protective Stop @ +2.0R)"),
        "C3": ("scratch/exp_c3_dev.json", "C3 (Protective Stop @ +2.5R)")
    }
    
    results = {}
    for code, (path, label) in files.items():
        trades = load_trades(path)
        if trades is not None:
            results[code] = compute_metrics(trades, label)
            print(f"Loaded {code}: {len(trades)} trades")
        else:
            print(f"File for {code} not yet available ({path})")
            
    with open("scratch/experiment_c_comparison.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved comparison to scratch/experiment_c_comparison.json")

if __name__ == "__main__":
    main()
