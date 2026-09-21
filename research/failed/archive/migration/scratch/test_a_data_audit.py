import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.data_manager import DataManager, ALL_ASSETS

SETS = {
    "Set 1": ["1M", "1w", "1d"],
    "Set 2": ["1w", "1d", "4h"],
    "Set 3": ["1d", "4h", "1h"],
    "Set 4": ["4h", "1h", "15m"],
    "Set 5": ["1h", "15m", "5m"],
    "Set 6": ["15m", "5m", "1m"],
}

def load_data(symbol: str, tf: str):
    fpath = DataManager.get_cache_filepath(symbol, tf)
    if not os.path.exists(fpath):
        clean_sym = symbol.replace("/", "").upper()
        alt = os.path.join(os.path.dirname(fpath), f"binance_{clean_sym}_{tf}.json")
        if os.path.exists(alt):
            fpath = alt
    if not os.path.exists(fpath):
        return None
    try:
        with open(fpath, "r") as f:
            raw = json.load(f)
        if not raw or not isinstance(raw, list):
            return None
        return raw
    except Exception:
        return None

def main():
    print("=========================================================================================================")
    print(f"{'Asset':<10} | {'Set':<6} | {'Status':<25} | {'Start Date (UTC)':<20} | {'End Date (UTC)':<20}")
    print("---------------------------------------------------------------------------------------------------------")
    
    matrix = []
    
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        for set_name, tfs in SETS.items():
            start_ts = 0
            end_ts = float('inf')
            missing = False
            for tf in tfs:
                data = load_data(symbol, tf)
                if not data or len(data) < 50:
                    missing = True
                    break
                
                # First timestamp
                ts_first = data[0][0] // 1000
                # Last timestamp
                ts_last = data[-1][0] // 1000
                
                start_ts = max(start_ts, ts_first)
                end_ts = min(end_ts, ts_last)
                
            if missing or start_ts >= end_ts:
                status = "INSUFFICIENT_DATA"
                start_str = "N/A"
                end_str = "N/A"
            else:
                status = "SUFFICIENT"
                start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                end_str = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                
            matrix.append({
                "asset": asset,
                "set_name": set_name,
                "status": status,
                "start": start_str,
                "end": end_str
            })
            
            print(f"{asset:<10} | {set_name:<6} | {status:<25} | {start_str:<20} | {end_str:<20}")
            
    print("=========================================================================================================")

if __name__ == "__main__":
    main()
