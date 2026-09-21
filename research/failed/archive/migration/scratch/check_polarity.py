import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
import json
from market_data.warehouse_loader import WarehouseLoader

with open("scratch/anchor2_dev_certified_results.json", "r") as f:
    d = json.load(f)

trades = d["all_trades"]
tf_map = {"SET_1": "1d", "SET_2": "4h", "SET_3": "1h", "SET_4": "15m"}

header = f"{'Trade ID':<45} | {'Dir':<12} | {'Open':<9} | {'Close':<9} | {'Candle':<8} | {'Matches?':<8} | {'Net R':<8} | {'MFE':<6} | {'MAE':<6}"
print(header)
print("-" * len(header))

matches_count = 0
counter_count = 0

counter_trades = []

for t in trades:
    sym = t["symbol"]
    tf_set = t["timeframe_set"]
    ltf = tf_map[tf_set]
    setup_ts = t["setup_timestamp"]
    dir_perm = t["directional_permission"]
    net_r = t["net_r"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    
    cache_file = f"market_data/cache/binance_{sym.replace('/', '')}_{ltf}.json"
    with open(cache_file, "r") as f:
        raw_candles = json.load(f)
    match = [r for r in raw_candles if r[0] == setup_ts * 1000]
    if match:
        row = match[0]
        o, c = float(row[1]), float(row[4])
        is_bull = c > o
        is_bear = c < o
        pol = "BULLISH" if is_bull else ("BEARISH" if is_bear else "DOJI")
        
        is_long = "LONG" in dir_perm
        matches = (is_long and is_bull) or ((not is_long) and is_bear)
        
        if matches:
            matches_count += 1
            m_str = "MATCH"
        else:
            counter_count += 1
            m_str = "COUNTER"
            counter_trades.append(t)
            
        tid = t["trade_id"]
        print(f"{tid:<45} | {dir_perm:<12} | {o:<9.2f} | {c:<9.2f} | {pol:<8} | {m_str:<8} | {net_r:<+8.4f} | {mfe:<6.2f} | {mae:<6.2f}")

print(f"\nTotal: {len(trades)}, Matches: {matches_count}, Counter: {counter_count}")
print("\nCounter trades breakdown:")
for ct in counter_trades:
    tid = ct["trade_id"]
    pnl = ct["net_r"]
    mfe = ct["mfe_r"]
    ex = ct["exit_reason"]
    print(f"  {tid} | Net R: {pnl:+.4f}R | MFE: {mfe:.2f}R | Exit: {ex}")
