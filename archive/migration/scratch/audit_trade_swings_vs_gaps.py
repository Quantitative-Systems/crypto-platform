import json
from datetime import datetime, timezone
import sys

sys.path.insert(0, "/home/mrcn2/crypto-platform")

with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
    replay_data = json.load(f)

trades = replay_data.get("all_trades", [])

with open("scratch/data_gap_inventory.json") as f:
    all_gaps = json.load(f)

in_dev_gaps = [g for g in all_gaps if g["is_in_dev_partition"]]

print(f"Auditing {len(trades)} executed trades against {len(in_dev_gaps)} in-dev gaps...")

# Let's inspect the setup timestamp, entry timestamp, and exit timestamp of each trade
# Gaps in 2021:
# 1. 2021-02-11 03:00 to 05:00 UTC (1613012400 to 1613019600)
# 2. 2021-03-06 01:00 to 03:00 UTC (1614992400 to 1614999600)
# 3. 2021-04-20 01:00 to 04:00 UTC (1618880400 to 1618891200)
# 4. 2021-04-25 04:00 to 08:00 UTC (1619323200 to 1619337600)
# 5. 2021-08-13 01:00 to 06:00 UTC (1628816400 to 1628834400)
# 6. 2021-09-29 06:00 to 09:00 UTC (1632895200 to 1632906000)

for i, t in enumerate(trades, 1):
    tid = t.get("trade_id")
    sym = t.get("symbol")
    stream = t.get("stream_id")
    entry_ts = t.get("entry_timestamp")
    exit_ts = t.get("exit_timestamp")
    setup_ts = t.get("setup_timestamp")
    
    entry_dt = datetime.fromtimestamp(entry_ts, tz=timezone.utc)
    exit_dt = datetime.fromtimestamp(exit_ts, tz=timezone.utc)
    setup_dt = datetime.fromtimestamp(setup_ts, tz=timezone.utc) if setup_ts else None
    
    print(f"\n--- Trade #{i:02d}: {tid} ({sym} {stream}) ---")
    print(f"  Setup: {setup_dt} | Entry: {entry_dt} | Exit: {exit_dt}")
    
    # Check distance to closest gap
    closest_gap = None
    min_dist_sec = float('inf')
    for g in in_dev_gaps:
        if g["symbol"] == sym:
            # Distance from entry to gap
            gap_center = (g["prev_timestamp"] + g["curr_timestamp"]) / 2.0
            dist = abs(entry_ts - gap_center)
            if dist < min_dist_sec:
                min_dist_sec = dist
                closest_gap = g
                
    if closest_gap:
        dist_days = round(min_dist_sec / 86400.0, 1)
        print(f"  Closest gap on {sym}: {closest_gap['timeframe']} from {closest_gap['prev_utc']} to {closest_gap['curr_utc']}")
        print(f"  Distance from entry to closest gap: {dist_days} days ({round(min_dist_sec / 3600.0, 1)} hours)")
        if entry_ts >= closest_gap["prev_timestamp"] and entry_ts <= closest_gap["curr_timestamp"]:
            print("  ⚠️ CRITICAL: ENTRY OCCURRED INSIDE A GAP!")
        elif exit_ts >= closest_gap["prev_timestamp"] and exit_ts <= closest_gap["curr_timestamp"]:
            print("  ⚠️ CRITICAL: EXIT OCCURRED INSIDE A GAP!")
        elif setup_ts and setup_ts >= closest_gap["prev_timestamp"] and setup_ts <= closest_gap["curr_timestamp"]:
            print("  ⚠️ CRITICAL: SETUP OCCURRED INSIDE A GAP!")
        else:
            print("  ✅ CLEAR: No temporal overlap with entry, exit, or setup.")
