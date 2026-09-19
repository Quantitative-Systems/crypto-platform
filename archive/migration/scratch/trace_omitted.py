import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trades = d1["all_trades"]
e1_trades = {t["trade_id"]: t for t in e1["all_trades"]}

omitted = [t for t in d1_trades if t["trade_id"] not in e1_trades]
print(f"Total omitted D1 trades: {len(omitted)}")

for i, t in enumerate(omitted):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    d1_entry_ts = t["entry_timestamp"]
    d1_entry_p = t["entry_price"]
    d1_sl = t["initial_stop_price"]
    d1_tp = t["target_price"]
    d1_rr = t["raw_rr"]
    d1_mfe = t["mfe_r"]
    d1_mae = t["mae_r"]
    d1_net = t["net_r"]
    d1_exit = t["exit_reason"]
    d1_trig = t["metadata"]["structural_provenance"].get("ltf_entry_reason")
    
    print("=" * 80)
    print(f"[{i+1:02d}] {cid} | {sym} | {st} | {dir_}")
    print(f"     D1 Trigger:  {d1_trig} at TS={d1_entry_ts}")
    print(f"     Would-be:    Entry={d1_entry_p} | SL={d1_sl} | TP={d1_tp} | Planned RR={d1_rr:.2f}R")
    print(f"     D1 Outcome:  Net R={d1_net:+.4f}R | MFE={d1_mfe:.2f}R | MAE={d1_mae:.2f}R | Exit={d1_exit}")
