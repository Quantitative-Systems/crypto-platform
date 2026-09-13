import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trades = {t["trade_id"]: t for t in d1["all_trades"]}
e1_trades = e1["all_trades"]

print("=== E1 13 TRADES ORIGIN ===")
for i, t in enumerate(e1_trades):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    entry_ts = t["entry_timestamp"]
    net_r = t["net_r"]
    exit_r = t["exit_reason"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    rr = t["raw_rr"]
    
    if cid in d1_trades:
        d1_t = d1_trades[cid]
        print(f"[{i+1:02d}] RETAINED: {cid} | {sym} {st} {dir_} | E1 Net={net_r:+.4f}R (D1 Net={d1_t['net_r']:+.4f}R) | E1 Entry TS={entry_ts} (D1 Entry TS={d1_t['entry_timestamp']})")
    else:
        print(f"[{i+1:02d}] NEW IN E1: {cid} | {sym} {st} {dir_} | E1 Net={net_r:+.4f}R | Exit={exit_r} | MFE={mfe:.2f}R | MAE={mae:.2f}R | RR={rr:.2f}R | Entry TS={entry_ts}")
