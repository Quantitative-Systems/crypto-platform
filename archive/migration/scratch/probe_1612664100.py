import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
import json
from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy

# Check D1 vs D2 configuration around 1612664100
symbol = "SOL/USDT"
htf_tf = "4h"
mtf_tf = "1h"
ltf_tf = "15m"

# Load candles
start_ms = 1612500000 * 1000
end_ms = 1612700000 * 1000

htf_candles = WarehouseLoader.load_history(symbol, htf_tf, limit=10000, start_time_ms=None, end_time_ms=end_ms)
mtf_candles = WarehouseLoader.load_history(symbol, mtf_tf, limit=10000, start_time_ms=None, end_time_ms=end_ms)
ltf_candles = WarehouseLoader.load_history(symbol, ltf_tf, limit=10000, start_time_ms=1609459200000, end_time_ms=end_ms)

print(f"Loaded {len(htf_candles)} HTF, {len(mtf_candles)} MTF, {len(ltf_candles)} LTF candles.")

# Find the index of LTF candle at 1612664100
target_ts = 1612664100
idx = None
for i, c in enumerate(ltf_candles):
    if c.timestamp == target_ts:
        idx = i
        break
print(f"Target TS {target_ts} found at LTF index {idx}")

# Run LanguageCoordinator at target_ts
lang_coord = LanguageCoordinator()
# slice up to target_ts
htf_sub = [c for c in htf_candles if c.timestamp <= target_ts]
mtf_sub = [c for c in mtf_candles if c.timestamp <= target_ts]
ltf_sub = [c for c in ltf_candles if c.timestamp <= target_ts]

htf_p = lang_coord.run(htf_sub, symbol, htf_tf)
mtf_p = lang_coord.run(mtf_sub, symbol, mtf_tf)
ltf_p = lang_coord.run(ltf_sub, symbol, ltf_tf)

print(f"HTF Trend: {htf_p.trend_state}, Phase: {htf_p.phase_state}, Keyzones: {len(htf_p.keyzones)}")
for kz in htf_p.keyzones:
    print(f"  KZ: {kz.zone_id} | {kz.zone_type} | {kz.low} - {kz.high} | Status: {getattr(kz, 'status', 'None')}")
