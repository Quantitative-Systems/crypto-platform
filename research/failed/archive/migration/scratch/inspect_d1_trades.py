import json

with open("scratch/exp_d1_dev.json") as f:
    d = json.load(f)

trades = d["all_trades"]
print(f"Total trades: {len(trades)}")
for i, t in enumerate(trades):
    sym = t.get("symbol", "N/A")
    st = t.get("timeframe_set") or t.get("stream", "N/A")
    dir_ = t.get("direction", "N/A")
    ts = t.get("entry_timestamp", 0)
    trig = t.get("metadata", {}).get("structural_provenance", {}).get("ltf_entry_reason", "N/A")
    pnl = t.get("net_r", 0.0)
    ex = t.get("exit_reason", "N/A")
    mfe = t.get("mfe_r", 0.0)
    mae = t.get("mae_r", 0.0)
    print(f"[{i+1:02d}] {sym:8s} | {st:6s} | {dir_:7s} | ts={ts} | trig={trig:42s} | net_r={pnl:+.4f}R | MFE={mfe:.2f}R | MAE={mae:.2f}R | exit={ex}")
