import json
import os
import numpy as np
import collections

files = [
    "scratch/trades_BTCUSDT_SET_3.json",
    "scratch/trades_ETHUSDT_SET_3.json",
    "scratch/trades_SOLUSDT_SET_3.json",
    "scratch/trades_BTCUSDT_SET_4.json",
    "scratch/trades_ETHUSDT_SET_4.json",
    "scratch/trades_SOLUSDT_SET_4.json"
]

all_trades = []
for f in files:
    if os.path.exists(f):
        with open(f) as fp:
            data = json.load(fp)
            all_trades.extend(data)

print(f"Loaded {len(all_trades)} trades for analysis.")

# Step 3: Stop-Distance
distances = []
small_dist_trades = []
for t in all_trades:
    entry = t["fill_entry_price"]
    stop = t["initial_stop_price"]
    dist = abs(entry - stop)
    distances.append(dist)
    if dist < 1e-4:
        small_dist_trades.append(t)

if distances:
    print("\n--- STEP 3: STOP DISTANCE ---")
    print(f"Min Dist: {np.min(distances):.6f}")
    print(f"Median Dist: {np.median(distances):.6f}")
    print(f"1st Percentile: {np.percentile(distances, 1):.6f}")
    print(f"Extreme Small Stop Trades: {len(small_dist_trades)}")
    if small_dist_trades:
        print("Example extremely small stop trade:")
        s = small_dist_trades[0]
        print(f"  ID: {s['trade_id']} | Sym: {s['symbol']} | Qty: {s['position_units']}")

# Step 4: Realized-R Audit
print("\n--- STEP 4: REALIZED R AUDIT ---")
def check_r(t):
    entry = t["fill_entry_price"]
    stop = t["initial_stop_price"]
    is_long = t["directional_permission"] == "PERMIT_LONG"
    risk_dist = (entry - stop) if is_long else (stop - entry)
    if risk_dist <= 0:
        return 0.0
    # Expected Risk was dollar_risk
    # R_dist = exit - entry (if long), entry - exit (if short)
    exit_p = t["exit_price"]
    gross_pnl = (exit_p - entry) * t["position_units"] if is_long else (entry - exit_p) * t["position_units"]
    net_pnl = gross_pnl - t["exit_fee"]
    calc_r = net_pnl / t["dollar_risk"] if t["dollar_risk"] > 0 else 0
    return calc_r

print("Sample R checks:")
for t in all_trades[:5]:
    calc_r = check_r(t)
    print(f"  {t['trade_id']}: Stored={t['net_r']:.4f} | Calc={calc_r:.4f}")

# Step 5: Exit Attribution
print("\n--- STEP 5: EXIT ATTRIBUTION ---")
for f in files:
    sym = f.split("_")[1] if "_" in f else ""
    tf = f.split("_")[2].replace(".json", "") if "_" in f else ""
    if os.path.exists(f):
        with open(f) as fp:
            data = json.load(fp)
            counts = collections.Counter([t["exit_reason"] for t in data])
            total = len(data)
            print(f"{sym} {tf}: {total} trades")
            for k,v in counts.items():
                print(f"  {k}: {v} ({v/total*100:.1f}%)")

# Step 6: MFE / MAE
print("\n--- STEP 6: MFE / MAE ---")
for f in files:
    if "SET_3" in f and os.path.exists(f):
        sym = f.split("_")[1]
        with open(f) as fp:
            data = json.load(fp)
            if not data: continue
            mfes, maes, win_rs, loss_rs = [], [], [], []
            eth_1r_loss = 0
            for t in data:
                entry = t["fill_entry_price"]
                stop = t["initial_stop_price"]
                risk_dist = abs(entry - stop)
                is_long = t["directional_permission"] == "PERMIT_LONG"
                meta = t.get("metadata", {})
                mfe_p = meta.get("mfe_price", entry)
                mae_p = meta.get("mae_price", entry)
                
                mfe_dist = (mfe_p - entry) if is_long else (entry - mfe_p)
                mae_dist = (entry - mae_p) if is_long else (mae_p - entry)
                
                mfe_r = mfe_dist / risk_dist if risk_dist > 0 else 0
                mae_r = mae_dist / risk_dist if risk_dist > 0 else 0
                
                mfes.append(mfe_r)
                maes.append(mae_r)
                
                r = t["net_r"]
                if r > 0: win_rs.append(r)
                else: loss_rs.append(r)
                
                if sym == "ETHUSDT" and mfe_r >= 1.0 and r < 0:
                    eth_1r_loss += 1
            
            print(f"{sym} SET_3:")
            print(f"  Avg MFE: {np.mean(mfes):.2f}R | Median MFE: {np.median(mfes):.2f}R")
            print(f"  Avg MAE: {np.mean(maes):.2f}R | Median MAE: {np.median(maes):.2f}R")
            print(f"  Avg Win R: {np.mean(win_rs) if win_rs else 0:.2f}R")
            print(f"  Avg Loss R: {np.mean(loss_rs) if loss_rs else 0:.2f}R")
            if sym == "ETHUSDT":
                print(f"  ETH Trades reaching +1R but losing: {eth_1r_loss}")
