import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trades = d1["all_trades"]
e1_trades = e1["all_trades"]

print(f"Total D1 Trades: {len(d1_trades)}")
print(f"Total E1 Trades: {len(e1_trades)}")

# Match by candidate_id or setup
print("\n--- D1 TRADES ANALYSIS ---")
for i, t in enumerate(d1_trades):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    d1_entry_ts = t["entry_timestamp"]
    d1_pnl = t["net_r"]
    d1_exit = t["exit_reason"]
    d1_mfe = t["mfe_r"]
    d1_mae = t["mae_r"]
    d1_trig = t["metadata"]["structural_provenance"].get("ltf_entry_reason")
    
    # Check if exact candidate is in E1
    e1_match = [x for x in e1_trades if x["trade_id"] == cid]
    # Check if same stream has a trade around that time
    e1_nearby = [x for x in e1_trades if x["symbol"] == sym and x["timeframe_set"] == st and abs(x["entry_timestamp"] - d1_entry_ts) < 7*86400]
    
    if e1_match:
        m = e1_match[0]
        status = "RETAINED_IDENTICAL" if m["entry_timestamp"] == d1_entry_ts else f"RETAINED_DELAYED (entered at {m['entry_timestamp']})"
        e1_pnl = m["net_r"]
        print(f"[{i+1:02d}] {cid} | {sym} {st} {dir_} | D1: ts={d1_entry_ts}, pnl={d1_pnl:+.4f}R, trig={d1_trig} | E1: {status}, pnl={e1_pnl:+.4f}R")
    elif e1_nearby:
        nb = e1_nearby[0]
        print(f"[{i+1:02d}] {cid} | {sym} {st} {dir_} | D1: ts={d1_entry_ts}, pnl={d1_pnl:+.4f}R, trig={d1_trig} | E1: DIFFERENT_CANDIDATE ({nb['trade_id']} at ts={nb['entry_timestamp']}, pnl={nb['net_r']:+.4f}R)")
    else:
        print(f"[{i+1:02d}] {cid} | {sym} {st} {dir_} | D1: ts={d1_entry_ts}, pnl={d1_pnl:+.4f}R, trig={d1_trig} | E1: OMITTED (No E1 trade in this window)")
