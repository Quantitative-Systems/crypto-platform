"""
Data integrity inspector for In-Sample (IS) vs Out-Of-Sample (OOS) partitions.
"""

import os
import json
from datetime import datetime, timezone

CACHE_DIR = "/home/mrcn2/crypto-platform/market_data/cache"

assets = ["BTC", "ETH", "SOL"]
timeframes = ["15m", "1h", "4h", "1d", "1w", "1M"]

print("=" * 100)
print("DATA INTEGRITY AUDIT: WAREHOUSE DATASET CATALOG")
print("=" * 100)

catalog = {}

for asset in assets:
    catalog[asset] = {}
    print(f"\n[{asset}USDT]")
    for tf in timeframes:
        fn = f"binance_{asset}USDT_{tf}.json"
        fp = os.path.join(CACHE_DIR, fn)
        if os.path.exists(fp):
            with open(fp, "r") as f:
                data = json.load(f)
            count = len(data)
            first_ts = int(data[0][0] // 1000)
            last_ts = int(data[-1][0] // 1000)
            first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            duration_days = (last_ts - first_ts) / 86400.0
            catalog[asset][tf] = {
                "count": count,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "first_dt": first_dt,
                "last_dt": last_dt,
                "duration_days": duration_days
            }
            print(f"  {tf:<4} | Count: {count:6d} | First: {first_dt} | Last: {last_dt} | Duration: {duration_days:6.1f} days")

# Check alignment across SET_3 (1D, 4H, 1H) and SET_4 (4H, 1H, 15M)
print("\n" + "=" * 100)
print("PROPOSED IS / OOS SPLIT AUDIT (Chronological 70% In-Sample / 30% Out-Of-Sample)")
print("=" * 100)

for asset in assets:
    # Look at 1H (SET_3 LTF) and 15M (SET_4 LTF)
    for ltf in ["1h", "15m"]:
        info = catalog[asset][ltf]
        total_c = info["count"]
        split_idx = int(total_c * 0.70)
        is_count = split_idx
        oos_count = total_c - split_idx
        
        fn = f"binance_{asset}USDT_{ltf}.json"
        with open(os.path.join(CACHE_DIR, fn), "r") as f:
            data = json.load(f)
            
        split_ts = int(data[split_idx][0] // 1000)
        split_dt = datetime.fromtimestamp(split_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        print(f"{asset}USDT {ltf:<4} | Total: {total_c} | IS: {is_count} (Start -> {split_dt}) | OOS: {oos_count} ({split_dt} -> End)")
