import json

with open("scratch/composite_01_dev_results.json") as f:
    old_data = json.load(f)

with open("scratch/composite_01_dev_results_repaired.json") as f:
    new_data = json.load(f)

old_trades = old_data.get("all_trades", [])
new_trades = new_data.get("all_trades", [])

print(f"Old Trades Count: {len(old_trades)}")
print(f"New Trades Count: {len(new_trades)}")

old_map = {t["trade_id"]: t for t in old_trades}
new_map = {t["trade_id"]: t for t in new_trades}

print("\n--- TRADES ELIMINATED IN REPAIRED ENGINE ---")
for tid, t in old_map.items():
    if tid not in new_map:
        print(f"Eliminated: {tid}")
        print(f"  Asset: {t.get('symbol')} | Set: {t.get('stream_id')} | Dir: {t.get('direction')}")
        print(f"  Entry: {t.get('entry_price')} | SL: {t.get('initial_stop_price')} | Target: {t.get('target_price')}")
        print(f"  Planned RR: {t.get('raw_rr')} | Net R: {t.get('net_r'):.4f} | Exit: {t.get('exit_reason')}")

print("\n--- NEW TRADES IN REPAIRED ENGINE ---")
new_count = 0
for tid, t in new_map.items():
    if tid not in old_map:
        new_count += 1
        print(f"New: {tid} | Asset: {t.get('symbol')} | Target: {t.get('target_price')}")
if new_count == 0:
    print("None. Exactly 0 new / spurious trades were spawned.")

print("\n--- COMPARISON OF THE 11 PERSISTENT TRADES ---")
print(f"{'#':<3} | {'Trade ID':<42} | {'Symbol':<8} | {'Entry':<9} | {'Target':<9} | {'Old Net R':<10} | {'New Net R':<10} | {'Diff R':<8} | {'Exit Reason'}")
print("-" * 125)
idx = 1
for tid, ot in old_map.items():
    if tid in new_map:
        nt = new_map[tid]
        diff_r = nt.get("net_r", 0) - ot.get("net_r", 0)
        target_str = f"{nt.get('target_price'):.2f}" if nt.get('target_price') is not None else "None"
        print(f"{idx:<3} | {tid:<42} | {nt.get('symbol'):<8} | {nt.get('entry_price', 0):<9.2f} | {target_str:<9} | {ot.get('net_r', 0):<10.4f} | {nt.get('net_r', 0):<10.4f} | {diff_r:<8.4f} | {nt.get('exit_reason')}")
        idx += 1

print("\n--- AGGREGATE PERFORMANCE METRICS COMPARISON ---")
old_agg = old_data.get("aggregate_performance", {})
new_agg = new_data.get("aggregate_performance", {})

metrics = ["total_trades", "win_rate", "profit_factor", "net_r", "expectancy", "max_drawdown_r", "gross_profit_r", "gross_loss_r"]
print(f"{'Metric':<20} | {'Old Composite (13 trades)':<28} | {'Repaired Composite (11 trades)':<28}")
print("-" * 80)
for m in metrics:
    print(f"{m:<20} | {str(old_agg.get(m)):<28} | {str(new_agg.get(m)):<28}")
