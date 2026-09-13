import json
import os
import sys
import numpy as np

sys.path.insert(0, "/home/mrcn2/crypto-platform")

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def compute_metrics(trades):
    n = len(trades)
    if n == 0:
        return {
            "n": 0, "wins": 0, "losses": 0, "be": 0, "win_rate": 0.0,
            "gross_r": 0.0, "friction_r": 0.0, "net_r": 0.0, "expectancy": 0.0,
            "profit_factor": 0.0, "max_dd": 0.0, "max_consec_losses": 0,
            "avg_mfe": 0.0, "median_mfe": 0.0, "avg_mae": 0.0, "median_mae": 0.0,
            "mfe_under_0_5": 0, "mfe_under_0_5_pct": 0.0,
            "mfe_under_1_0": 0, "mfe_under_1_0_pct": 0.0,
            "mfe_ge_1_5": 0, "mfe_ge_1_5_pct": 0.0,
            "mfe_ge_2_0": 0, "mfe_ge_2_0_pct": 0.0,
            "avg_time_to_mfe_hr": 0.0, "median_time_to_mfe_hr": 0.0
        }

    wins = [t for t in trades if t.get("net_r", 0) > 0.05]
    losses = [t for t in trades if t.get("net_r", 0) < -0.05]
    bes = [t for t in trades if abs(t.get("net_r", 0)) <= 0.05]

    win_rate = (len(wins) / n) * 100
    gross_r = sum(t.get("gross_r", t.get("net_r", 0)) for t in trades)
    net_r = sum(t.get("net_r", 0) for t in trades)
    friction_r = sum((t.get("fees_r", 0) + t.get("slippage_r", 0) + t.get("funding_r", 0)) for t in trades)
    expectancy = net_r / n

    total_win_r = sum(t.get("net_r", 0) for t in wins)
    total_loss_r = abs(sum(t.get("net_r", 0) for t in losses))
    pf = (total_win_r / total_loss_r) if total_loss_r > 0 else (999.0 if total_win_r > 0 else 0.0)

    # Max Drawdown & Max consecutive losses
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    sorted_trades = sorted(trades, key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)
    consec_losses = 0
    max_consec_losses = 0
    for t in sorted_trades:
        nr = t.get("net_r", 0)
        equity += nr
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
        if nr < -0.05:
            consec_losses += 1
            if consec_losses > max_consec_losses:
                max_consec_losses = consec_losses
        else:
            consec_losses = 0

    mfes = [t.get("mfe_r", 0) for t in trades]
    maes = [t.get("mae_r", 0) for t in trades]
    time_to_mfes = [t.get("metadata", {}).get("time_to_mfe", 0) / 3600.0 for t in trades]

    mfe_under_0_5 = sum(1 for m in mfes if m < 0.5)
    mfe_under_1_0 = sum(1 for m in mfes if m < 1.0)
    mfe_ge_1_5 = sum(1 for m in mfes if m >= 1.5)
    mfe_ge_2_0 = sum(1 for m in mfes if m >= 2.0)

    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "be": len(bes),
        "win_rate": win_rate,
        "gross_r": gross_r,
        "friction_r": friction_r,
        "net_r": net_r,
        "expectancy": expectancy,
        "profit_factor": pf,
        "max_dd": max_dd,
        "max_consec_losses": max_consec_losses,
        "avg_mfe": float(np.mean(mfes)) if mfes else 0.0,
        "median_mfe": float(np.median(mfes)) if mfes else 0.0,
        "avg_mae": float(np.mean(maes)) if maes else 0.0,
        "median_mae": float(np.median(maes)) if maes else 0.0,
        "mfe_under_0_5": mfe_under_0_5,
        "mfe_under_0_5_pct": (mfe_under_0_5 / n) * 100,
        "mfe_under_1_0": mfe_under_1_0,
        "mfe_under_1_0_pct": (mfe_under_1_0 / n) * 100,
        "mfe_ge_1_5": mfe_ge_1_5,
        "mfe_ge_1_5_pct": (mfe_ge_1_5 / n) * 100,
        "mfe_ge_2_0": mfe_ge_2_0,
        "mfe_ge_2_0_pct": (mfe_ge_2_0 / n) * 100,
        "avg_time_to_mfe_hr": float(np.mean(time_to_mfes)) if time_to_mfes else 0.0,
        "median_time_to_mfe_hr": float(np.median(time_to_mfes)) if time_to_mfes else 0.0,
    }

def run_attribution(trades, key_name):
    groups = {}
    for t in trades:
        k = t.get(key_name)
        if not k and key_name == "timeframe_set":
            k = t.get("stream_id", "").split("_", 1)[-1]
        elif not k and key_name == "asset":
            k = t.get("symbol", "").split("/")[0]
        if k not in groups:
            groups[k] = []
        groups[k].append(t)
    res = {}
    for k, v in sorted(groups.items()):
        res[k] = compute_metrics(v)
    return res

if __name__ == "__main__":
    d_e1 = load_json("scratch/exp_e1_dev.json")
    if not d_e1:
        print("E1 results not loaded.")
        sys.exit(1)
    print("Ready to process.")
