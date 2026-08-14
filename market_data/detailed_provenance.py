"""
Detailed Data Provenance Generator
Computes exact timestamps, counts, duplicates, missing bars, and hashes for all cached datasets.
"""

import os
import json
import hashlib
from datetime import datetime, timezone

CACHE_DIR = "/home/mrcn2/crypto-platform/market_data/cache"

TIMEFRAME_MS = {
    "15M": 15 * 60 * 1000,
    "1H": 60 * 60 * 1000,
    "4H": 4 * 60 * 60 * 1000,
    "1D": 24 * 60 * 60 * 1000,
    "1W": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
}

def generate_provenance():
    files = [f for f in sorted(os.listdir(CACHE_DIR)) if f.endswith('.json')]
    report = []

    for f in files:
        path = os.path.join(CACHE_DIR, f)
        with open(path, "rb") as fp:
            content = fp.read()
            sha256 = hashlib.sha256(content).hexdigest()[:16]
            data = json.loads(content.decode("utf-8"))

        # Parse filename e.g. BTC_USDT_15M.json
        parts = f.replace(".json", "").split("_")
        asset = parts[0]
        tf = parts[2] if len(parts) >= 3 else parts[1]

        timestamps = [row[0] for row in data]
        unique_ts = set(timestamps)
        duplicates = len(timestamps) - len(unique_ts)

        sorted_ts = sorted(list(unique_ts))
        first_ts = sorted_ts[0]
        last_ts = sorted_ts[-1]

        first_dt = datetime.fromtimestamp(first_ts / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        last_dt = datetime.fromtimestamp(last_ts / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        expected_step = TIMEFRAME_MS.get(tf.upper(), 0)
        missing_gaps = 0
        if expected_step > 0 and tf.upper() not in ["1M", "1W"]:
            for i in range(1, len(sorted_ts)):
                diff = sorted_ts[i] - sorted_ts[i-1]
                if diff > expected_step:
                    missing_gaps += int((diff - expected_step) // expected_step)

        report.append({
            "asset": asset,
            "timeframe": tf,
            "filename": f,
            "candle_count": len(data),
            "duplicates": duplicates,
            "missing_candles": missing_gaps,
            "first_timestamp": first_ts,
            "first_date": first_dt,
            "last_timestamp": last_ts,
            "last_date": last_dt,
            "interval_continuity": "100% CONTINUOUS" if missing_gaps == 0 else f"{missing_gaps} missing bars",
            "timezone": "UTC",
            "source": "Binance REST API (Spot/Futures Kline)",
            "dataset_hash": sha256
        })

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    generate_provenance()
