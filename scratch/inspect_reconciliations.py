import json

print("=== H0 RECONCILIATION ===")
with open("scratch/h0_dev_certified_results.json", "r") as f:
    h0_data = json.load(f)

print("H0 Aggregate Performance:")
for k, v in h0_data["aggregate_performance"].items():
    print(f"  {k}: {v}")

h0_trades = h0_data["all_trades"]
print(f"\nH0 Total Closed Trades: {len(h0_trades)}")
seen_h0 = set()
unresolved_h0 = 0
for i, t in enumerate(h0_trades):
    tid = t["trade_id"]
    is_dup = tid in seen_h0
    seen_h0.add(tid)
    status = t["status"]
    if status != "CLOSED":
        unresolved_h0 += 1
    mfe = t.get("mfe_r", 0.0)
    mae = t.get("mae_r", 0.0)
    pnl = t.get("realized_pnl_r", 0.0)
    entry_p = t.get("entry_price")
    exit_p = t.get("exit_price")
    exit_r = t.get("exit_reason")
    sym = t.get("symbol")
    tf = t.get("timeframe_set")
    print(f"[{i+1:02d}] ID: {tid} | {sym} {tf} | PnL: {pnl:+.4f}R | Status: {status} | Reason: {exit_r} | MFE: {mfe:.2f}R | MAE: {mae:.2f}R | Dup: {is_dup}")

print(f"H0 Duplicate count: {len(h0_trades) - len(seen_h0)}, Unresolved: {unresolved_h0}")

print("\n=== ANCHOR_2 RECONCILIATION ===")
with open("scratch/anchor2_dev_certified_results.json", "r") as f:
    a2_data = json.load(f)

print("ANCHOR_2 Aggregate Performance:")
for k, v in a2_data["aggregate_performance"].items():
    print(f"  {k}: {v}")

a2_trades = a2_data["all_trades"]
print(f"\nANCHOR_2 Total Closed Trades: {len(a2_trades)}")
seen_a2 = set()
unresolved_a2 = 0
for i, t in enumerate(a2_trades):
    tid = t["trade_id"]
    is_dup = tid in seen_a2
    seen_a2.add(tid)
    status = t["status"]
    if status != "CLOSED":
        unresolved_a2 += 1
    mfe = t.get("mfe_r", 0.0)
    mae = t.get("mae_r", 0.0)
    pnl = t.get("realized_pnl_r", 0.0)
    entry_p = t.get("entry_price")
    exit_p = t.get("exit_price")
    exit_r = t.get("exit_reason")
    sym = t.get("symbol")
    tf = t.get("timeframe_set")
    print(f"[{i+1:02d}] ID: {tid} | {sym} {tf} | PnL: {pnl:+.4f}R | Status: {status} | Reason: {exit_r} | MFE: {mfe:.2f}R | MAE: {mae:.2f}R | Dup: {is_dup}")

print(f"ANCHOR_2 Duplicate count: {len(a2_trades) - len(seen_a2)}, Unresolved: {unresolved_a2}")

print("\n=== STREAM LEVEL BREAKDOWN ===")
for s in a2_data["stream_results"]:
    print(s.get("stream_id"), list(s.keys()))
    metrics = s.get("metrics", {})
    print(f"  Trades: {metrics.get('total_trades')}, Net PnL: {metrics.get('net_pnl_r'):.4f}R, WR: {metrics.get('win_rate'):.1f}%")

