import json
from datetime import datetime, timezone

with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
    data = json.load(f)

trades = data.get("all_trades", [])

with open("scratch/data_gap_inventory.json") as f:
    all_gaps = json.load(f)

in_dev_gaps = [g for g in all_gaps if g["is_in_dev_partition"]]

# Unique gap windows
gap_windows = []
seen = set()
for g in in_dev_gaps:
    key = (g["prev_timestamp"], g["curr_timestamp"])
    if key not in seen:
        seen.add(key)
        gap_windows.append({
            "prev_ts": g["prev_timestamp"],
            "curr_ts": g["curr_timestamp"],
            "prev_utc": g["prev_utc"],
            "curr_utc": g["curr_utc"],
            "duration_h": g["duration_hours"],
            "affected_tfs": set([g["timeframe"] for g in in_dev_gaps if g["prev_timestamp"] == g["prev_timestamp"] and g["curr_timestamp"] == g["curr_timestamp"]]),
            "affected_symbols": set([g["symbol"] for g in in_dev_gaps if g["prev_timestamp"] == g["prev_timestamp"] and g["curr_timestamp"] == g["curr_timestamp"]])
        })

print(f"Total Unique In-Development Gap Windows: {len(gap_windows)}")
for idx, gw in enumerate(gap_windows, 1):
    print(f"Window #{idx}: {gw['prev_utc']} -> {gw['curr_utc']} ({gw['duration_h']}h)")

print("\n" + "=" * 100)
print(f"{'#':<3} | {'Trade ID':<35} | {'Symbol':<8} | {'Entry UTC':<20} | {'Exit UTC':<20} | {'Active Overlap?':<16} | {'Lookback Overlap?'}")
print("=" * 100)

for i, t in enumerate(trades, 1):
    tid = t.get("trade_id")
    sym = t.get("symbol")
    entry_ts = t.get("entry_timestamp")
    exit_ts = t.get("exit_timestamp")
    setup_ts = t.get("setup_timestamp")
    
    entry_utc = datetime.fromtimestamp(entry_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if entry_ts else "N/A"
    exit_utc = datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if exit_ts else "N/A"
    
    # Active overlap: does gap overlap [entry_ts, exit_ts]?
    active_overlaps = []
    for gw in gap_windows:
        # Overlap if max(start1, start2) < min(end1, end2)
        if max(entry_ts, gw["prev_ts"]) < min(exit_ts, gw["curr_ts"]):
            active_overlaps.append(gw)
            
    # Lookback overlap: lookback window (e.g. 50 bars preceding entry, or setup_ts to entry_ts)
    # Let's check 7 days preceding entry
    lookback_start = entry_ts - (7 * 24 * 3600)
    lookback_overlaps = []
    for gw in gap_windows:
        if max(lookback_start, gw["prev_ts"]) < min(entry_ts, gw["curr_ts"]):
            lookback_overlaps.append(gw)
            
    act_str = f"YES ({len(active_overlaps)})" if active_overlaps else "NO"
    lb_str = f"YES ({len(lookback_overlaps)})" if lookback_overlaps else "NO"
    
    print(f"{i:02d} | {tid[:35]:<35} | {sym:<8} | {entry_utc:<20} | {exit_utc:<20} | {act_str:<16} | {lb_str}")
    if active_overlaps:
        for ao in active_overlaps:
            print(f"     -> ACTIVE GAP: {ao['prev_utc']} -> {ao['curr_utc']}")
    if lookback_overlaps:
        for lo in lookback_overlaps:
            print(f"     -> LOOKBACK GAP: {lo['prev_utc']} -> {lo['curr_utc']}")

