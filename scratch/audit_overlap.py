from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4"]

print(f"{'Stream':<15} | {'HTF Start':<20} | {'MTF Start':<20} | {'LTF Start':<20} | {'End':<20} | {'Common Start':<20} | Usable")
print("-" * 125)

for asset in ASSETS:
    for tf_set_id in TF_SETS:
        tf_set = TimeframeAligner.get_set(tf_set_id)
        htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=50000)
        mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=50000)
        ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=50000)
        
        if not htf_candles or not mtf_candles or not ltf_candles:
            continue
            
        htf_s = htf_candles[0].timestamp
        mtf_s = mtf_candles[0].timestamp
        ltf_s = ltf_candles[0].timestamp
        
        latest = min(htf_candles[-1].timestamp, mtf_candles[-1].timestamp, ltf_candles[-1].timestamp)
        common_start = max(htf_s, mtf_s, ltf_s)
        
        from datetime import datetime, timezone
        def ts2str(ts):
            # assume ms for now, WarehouseLoader returns ms
            return datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if ts > 100000000000 else datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')

        print(f"{asset}_{tf_set_id:<11} | {ts2str(htf_s):<20} | {ts2str(mtf_s):<20} | {ts2str(ltf_s):<20} | {ts2str(latest):<20} | {ts2str(common_start):<20} | {'YES' if common_start < latest else 'NO'}")
