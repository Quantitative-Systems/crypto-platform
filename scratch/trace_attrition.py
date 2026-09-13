import json
import numpy as np

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trades = d1["all_trades"]
e1_trades = e1["all_trades"]

# 1. Attribution by Asset
print("=== ASSET ATTRIBUTION ===")
for asset in ["BTC", "ETH", "SOL"]:
    t_d1 = [t for t in d1_trades if asset in t["symbol"]]
    t_e1 = [t for t in e1_trades if asset in t["symbol"]]
    
    n_d1 = len(t_d1)
    net_d1 = sum(t["net_r"] for t in t_d1)
    e_d1 = net_d1 / n_d1 if n_d1 else 0
    w_d1 = len([t for t in t_d1 if t["net_r"] > 0.05])
    
    n_e1 = len(t_e1)
    net_e1 = sum(t["net_r"] for t in t_e1)
    e_e1 = net_e1 / n_e1 if n_e1 else 0
    w_e1 = len([t for t in t_e1 if t["net_r"] > 0.05])
    
    print(f"{asset:<5} | D1: N={n_d1:2d}, W={w_d1}, Net R={net_d1:+7.4f}R, E={e_d1:+7.4f}R | E1: N={n_e1:2d}, W={w_e1}, Net R={net_e1:+7.4f}R, E={e_e1:+7.4f}R")

# 2. Attribution by Timeframe Set
print("\n=== TIMEFRAME SET ATTRIBUTION ===")
for s in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
    t_d1 = [t for t in d1_trades if t.get("timeframe_set") == s]
    t_e1 = [t for t in e1_trades if t.get("timeframe_set") == s]
    
    n_d1 = len(t_d1)
    net_d1 = sum(t["net_r"] for t in t_d1)
    e_d1 = net_d1 / n_d1 if n_d1 else 0
    w_d1 = len([t for t in t_d1 if t["net_r"] > 0.05])
    
    n_e1 = len(t_e1)
    net_e1 = sum(t["net_r"] for t in t_e1)
    e_e1 = net_e1 / n_e1 if n_e1 else 0
    w_e1 = len([t for t in t_e1 if t["net_r"] > 0.05])
    
    print(f"{s:<5} | D1: N={n_d1:2d}, W={w_d1}, Net R={net_d1:+7.4f}R, E={e_d1:+7.4f}R | E1: N={n_e1:2d}, W={w_e1}, Net R={net_e1:+7.4f}R, E={e_e1:+7.4f}R")

# 3. Opportunity Attrition Details
print("\n=== DETAILED ATTRITION TRACE ===")
e1_ids = {t["trade_id"]: t for t in e1_trades}

for i, t in enumerate(d1_trades):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    trig = t["metadata"]["structural_provenance"].get("ltf_entry_reason", "")
    ts = t["entry_timestamp"]
    net_r = t["net_r"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    exit_r = t["exit_reason"]
    ep = t["entry_price"]
    sl = t["initial_stop_price"]
    tp = t["target_price"]
    rr = t["raw_rr"]
    
    in_e1 = cid in e1_ids
    print(f"D1-{i+1:02d} | {cid} | {sym} | {st} | {t['direction']} | trig={trig} | In E1: {in_e1} | Net={net_r:+.4f}R | MFE={mfe:.2f}R | Exit={exit_r}")
