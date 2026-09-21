import json
from collections import defaultdict

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

by_asset = defaultdict(lambda: {"total": 0, "win": 0, "be": 0, "loss": 0, "net_r": 0.0})
by_tf = defaultdict(lambda: {"total": 0, "win": 0, "be": 0, "loss": 0, "net_r": 0.0})

for t in c1["all_trades"]:
    asset = t["symbol"].split("/")[0]
    tf = t["timeframe_set"]
    nr = t["net_r"]
    reason = t["exit_reason"]
    
    for k, d in [(asset, by_asset), (tf, by_tf)]:
        d[k]["total"] += 1
        d[k]["net_r"] += nr
        if reason == "HTF_TP":
            d[k]["win"] += 1
        elif reason == "BREAKEVEN_TRAIL":
            d[k]["be"] += 1
        else:
            d[k]["loss"] += 1

print("=== ASSET BREAKDOWN (C1) ===")
print("{:<6} | {:<5} | {:<3} | {:<2} | {:<4} | {:>9} | {:>9}".format("Asset", "Total", "Win", "BE", "Loss", "Net R", "Loss Rate"))
print("-" * 55)
for asset in sorted(by_asset.keys()):
    d = by_asset[asset]
    lr = d["loss"] / d["total"] * 100
    print("{:<6} | {:<5} | {:<3} | {:<2} | {:<4} | {:>9.4f} | {:>8.1f}%".format(asset, d["total"], d["win"], d["be"], d["loss"], d["net_r"], lr))

print("\n=== TIMEFRAME SET BREAKDOWN (C1) ===")
print("{:<6} | {:<5} | {:<3} | {:<2} | {:<4} | {:>9} | {:>9}".format("TF Set", "Total", "Win", "BE", "Loss", "Net R", "Loss Rate"))
print("-" * 55)
for tf in sorted(by_tf.keys()):
    d = by_tf[tf]
    lr = d["loss"] / d["total"] * 100
    print("{:<6} | {:<5} | {:<3} | {:<2} | {:<4} | {:>9.4f} | {:>8.1f}%".format(tf, d["total"], d["win"], d["be"], d["loss"], d["net_r"], lr))
