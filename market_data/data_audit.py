import os
import json
from datetime import datetime

CACHE_DIR = "/home/mrcn2/crypto-platform/market_data/cache"

def audit_data():
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')]
    report = {}

    for f in sorted(files):
        path = os.path.join(CACHE_DIR, f)
        try:
            with open(path, 'r') as fp:
                data = json.load(fp)
        except Exception as e:
            report[f] = {"error": str(e)}
            continue
        
        if not data:
            report[f] = {"error": "Empty data"}
            continue
            
        # Data format is likely list of dicts or list of lists.
        # Check first element to determine format.
        # Assuming Binance format: [open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore]
        # Or standard dict: {"timestamp": ..., "open": ..., }
        
        first = data[0]
        if isinstance(first, list):
            get_ts = lambda x: x[0]
        elif isinstance(first, dict):
            get_ts = lambda x: x.get('timestamp') or x.get('open_time') or x.get('time')
        else:
            report[f] = {"error": "Unknown format"}
            continue
            
        timestamps = [get_ts(row) for row in data]
        
        if any(ts is None for ts in timestamps):
            report[f] = {"error": "Missing timestamps"}
            continue
            
        timestamps.sort()
        start_time = datetime.fromtimestamp(timestamps[0] / 1000.0) if timestamps[0] > 10**11 else datetime.fromtimestamp(timestamps[0])
        end_time = datetime.fromtimestamp(timestamps[-1] / 1000.0) if timestamps[-1] > 10**11 else datetime.fromtimestamp(timestamps[-1])
        
        intervals = set()
        for i in range(1, len(timestamps)):
            intervals.add(timestamps[i] - timestamps[i-1])
            
        report[f] = {
            "num_candles": len(data),
            "start_time": str(start_time),
            "end_time": str(end_time),
            "intervals": list(intervals),
            "is_continuous": len(intervals) == 1
        }
        
    print(json.dumps(report, indent=4))

if __name__ == "__main__":
    audit_data()
