import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, "/home/mrcn2/crypto-platform")

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier

ASSETS = ["BTC", "ETH", "SOL"]
TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "5m", "1m"]

DEV_START_SEC = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
DEV_END_SEC = int(datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp())

DEV_START_MS = DEV_START_SEC * 1000
DEV_END_MS = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

print(f"Development Partition (sec): {DEV_START_SEC} to {DEV_END_SEC}")

def find_gaps_in_candles(candles, tf_str, symbol):
    if not candles or len(candles) < 2:
        return []
    
    expected_interval = DataCertifier._tf_to_seconds(tf_str)
    gaps = []
    
    for i in range(1, len(candles)):
        prev = candles[i - 1]
        curr = candles[i]
        diff = curr.timestamp - prev.timestamp
        
        # 1M has variable days (28-31 days), so skip standard gap check for 1M
        if tf_str.upper() in ["1M", "1MO"]:
            continue
            
        if diff > expected_interval:
            missing_bars = (diff / expected_interval) - 1
            if missing_bars >= 1.0:
                is_in_dev = not (curr.timestamp < DEV_START_SEC or prev.timestamp > DEV_END_SEC)
                gap_info = {
                    "symbol": symbol,
                    "timeframe": tf_str,
                    "prev_timestamp": prev.timestamp,
                    "prev_utc": datetime.fromtimestamp(prev.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "curr_timestamp": curr.timestamp,
                    "curr_utc": datetime.fromtimestamp(curr.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "expected_interval_sec": expected_interval,
                    "diff_sec": diff,
                    "missing_bars": round(missing_bars, 2),
                    "duration_hours": round(diff / 3600.0, 2),
                    "is_in_dev_partition": is_in_dev,
                    "period_classification": "IN_DEVELOPMENT" if is_in_dev else ("PRE_DEV_WARMUP" if curr.timestamp <= DEV_START_SEC else "POST_DEV")
                }
                gaps.append(gap_info)
    return gaps

all_inventory_gaps = []

for asset in ASSETS:
    symbol = f"{asset}/USDT"
    for tf in ["1w", "1d", "4h", "1h", "15m"]:
        try:
            candles = WarehouseLoader.load_history(symbol, tf, limit=1_000_000, start_time_ms=None, end_time_ms=DEV_END_MS)
            gaps = find_gaps_in_candles(candles, tf, symbol)
            for g in gaps:
                g["candles_count"] = len(candles)
                g["first_candle_utc"] = datetime.fromtimestamp(candles[0].timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                g["last_candle_utc"] = datetime.fromtimestamp(candles[-1].timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                all_inventory_gaps.append(g)
        except Exception as e:
            print(f"Could not load {symbol} {tf}: {e}")

# Save full gap inventory
with open("scratch/data_gap_inventory.json", "w") as fp:
    json.dump(all_inventory_gaps, fp, indent=2)

print(f"Total gaps found across loaded warehouse datasets: {len(all_inventory_gaps)}")
in_dev_gaps = [g for g in all_inventory_gaps if g["is_in_dev_partition"]]
pre_dev_gaps = [g for g in all_inventory_gaps if not g["is_in_dev_partition"]]
print(f"  Pre-Development Warmup Gaps (before 2021-01-01): {len(pre_dev_gaps)}")
print(f"  In-Development Partition Gaps (2021-01-01 to 2022-12-31): {len(in_dev_gaps)}")

print("\n--- IN-DEVELOPMENT GAPS BREAKDOWN ---")
for g in in_dev_gaps:
    print(f"[{g['symbol']} {g['timeframe']:>3s}] {g['prev_utc']} -> {g['curr_utc']} | Missing {g['missing_bars']} bars ({g['duration_hours']}h)")
