import json
import numpy as np

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)["all_trades"]
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)["all_trades"]

def analyze_dist(trades, label):
    mfes = [t.get("mfe_r", 0.0) for t in trades]
    maes = [t.get("mae_r", 0.0) for t in trades]
    tt_mfes = [t.get("metadata", {}).get("time_to_mfe", 0.0) / 3600.0 for t in trades]
    n = len(trades)
    
    print(f"=== {label} (N={n}) ===")
    print(f"MFE Mean:      {np.mean(mfes):.2f}R")
    print(f"MFE Median:    {np.median(mfes):.2f}R")
    print(f"MFE 25th Pct:  {np.percentile(mfes, 25):.2f}R")
    print(f"MFE 75th Pct:  {np.percentile(mfes, 75):.2f}R")
    print(f"MFE < 0.5R:    {sum(1 for m in mfes if m < 0.5)} ({sum(1 for m in mfes if m < 0.5)/n*100:.1f}%)")
    print(f"MFE < 1.0R:    {sum(1 for m in mfes if m < 1.0)} ({sum(1 for m in mfes if m < 1.0)/n*100:.1f}%)")
    print(f"MFE >= 1.5R:   {sum(1 for m in mfes if m >= 1.5)} ({sum(1 for m in mfes if m >= 1.5)/n*100:.1f}%)")
    print(f"MFE >= 2.0R:   {sum(1 for m in mfes if m >= 2.0)} ({sum(1 for m in mfes if m >= 2.0)/n*100:.1f}%)")
    print(f"MAE Mean:      {np.mean(maes):.2f}R")
    print(f"MAE Median:    {np.median(maes):.2f}R")
    print(f"MAE 25th Pct:  {np.percentile(maes, 25):.2f}R")
    print(f"MAE 75th Pct:  {np.percentile(maes, 75):.2f}R")
    print(f"Time to MFE Mean:   {np.mean(tt_mfes):.1f} hours")
    print(f"Time to MFE Median: {np.median(tt_mfes):.1f} hours")
    print()

analyze_dist(d1, "D1 Control")
analyze_dist(e1, "E1 Treatment")
