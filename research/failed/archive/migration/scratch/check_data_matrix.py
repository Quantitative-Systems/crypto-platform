import os
import json
from datetime import datetime, timezone

cache_dir = "market_data/cache"
assets = ["BTC", "ETH", "SOL"]
tfs = ["1M", "1w", "1d", "4h", "1h", "15m", "5m", "1m"]

def tf_sec(tf):
    if tf == "1m": return 60
    if tf == "5m": return 300
    if tf == "15m": return 900
    if tf == "1h": return 3600
    if tf == "4h": return 14400
    if tf == "1d": return 86400
    if tf == "1w": return 604800
    if tf == "1M": return 2592000
    return 3600

dev_start_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
dev_end_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

print(f"{'Asset':<5} | {'TF':<4} | {'Total Bars':<10} | {'Earliest (UTC)':<17} | {'Latest (UTC)':<17} | {'Dups':<5} | {'Invals':<6} | {'Gaps':<5} | {'Dev Bars':<8} | {'Usable Dev Coverage'}")
print("-" * 135)

for asset in assets:
    for tf in tfs:
        fname = f"binance_{asset}USDT_{tf}.json"
        fpath = os.path.join(cache_dir, fname)
        if not os.path.exists(fpath):
            print(f"{asset:<5} | {tf:<4} | MISSING FILE")
            continue
        with open(fpath, "r") as f:
            data = json.load(f)
        total_bars = len(data)
        if total_bars == 0:
            print(f"{asset:<5} | {tf:<4} | EMPTY")
            continue
        
        seen = set()
        dups = 0
        invals = 0
        gaps = 0
        interval_ms = tf_sec(tf) * 1000
        
        earliest_ts = data[0][0]
        latest_ts = data[-1][0]
        
        dev_bars = 0
        dev_gaps = 0
        
        prev_ts = None
        for row in data:
            ts = row[0]
            if ts in seen:
                dups += 1
            seen.add(ts)
            o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
            if h < l or c > h or c < l or o > h or o < l:
                invals += 1
            if prev_ts is not None and tf != "1M":
                diff = ts - prev_ts
                if diff > interval_ms:
                    gap_bars = int((diff / interval_ms) - 1)
                    if gap_bars >= 1:
                        gaps += 1
                        if dev_start_ms <= ts < dev_end_ms:
                            dev_gaps += 1
            prev_ts = ts
            if dev_start_ms <= ts < dev_end_ms:
                dev_bars += 1
                
        earliest_dt = datetime.fromtimestamp(earliest_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        latest_dt = datetime.fromtimestamp(latest_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        
        if tf == "1M": expected_dev = 24
        elif tf == "1w": expected_dev = 104
        elif tf == "1d": expected_dev = 730
        elif tf == "4h": expected_dev = 4380
        elif tf == "1h": expected_dev = 17520
        elif tf == "15m": expected_dev = 70080
        elif tf == "5m": expected_dev = 210240
        elif tf == "1m": expected_dev = 1051200
        else: expected_dev = 1
        
        pct = (dev_bars / expected_dev) * 100.0 if expected_dev > 0 else 0.0
        if dev_bars == 0:
            dev_cov = "0% (Post-2023 Cache Only - Fail Closed)"
        elif pct >= 99.5:
            dev_cov = f"100% Usable ({dev_bars}/{expected_dev}, {dev_gaps} gaps)"
        else:
            dev_cov = f"{pct:.1f}% ({dev_bars}/{expected_dev}, {dev_gaps} gaps)"
            
        print(f"{asset:<5} | {tf:<4} | {total_bars:<10} | {earliest_dt:<17} | {latest_dt:<17} | {dups:<5} | {invals:<6} | {gaps:<5} | {dev_bars:<8} | {dev_cov}")
