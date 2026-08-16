import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from market_intelligence.primitives import TrendDirection

loader = WarehouseLoader()
htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)

coordinator = LanguageCoordinator(buffer_size=300)

trends_seen = {}
phases_seen = {}
biases_seen = {}

for i in range(15, len(htf_candles)):
    slice_c = htf_candles[max(0, i - 80):i + 1]
    htf_state = coordinator.run(slice_c, symbol="BTCUSDT", timeframe="1D")
    
    # Check structure_state.external_trend directly vs TrendDirection
    ext_trend_val = htf_state.structure_state.external_trend.value
    # Convert to primitives TrendDirection
    prim_trend = TrendDirection(ext_trend_val)
    
    # Re-evaluate bias with primitive trend
    # Replace trend_state on payload
    object.__setattr__(htf_state, 'trend_state', prim_trend)
    
    b = BiasClassifier.evaluate(htf_state)
    
    trends_seen[prim_trend.value] = trends_seen.get(prim_trend.value, 0) + 1
    biases_seen[b.value] = biases_seen.get(b.value, 0) + 1

print("\n--- 1D HTF WITH UNIFIED ENUMS ---")
print("External Trends seen (1D):", trends_seen)
print("HTF Biases seen (1D):", biases_seen)

# Now check 4H MTF
mtf_trends = {}
for i in range(15, min(2000, len(mtf_candles))):
    slice_c = mtf_candles[max(0, i - 100):i + 1]
    mtf_state = coordinator.run(slice_c, symbol="BTCUSDT", timeframe="4H")
    ext_trend_val = mtf_state.structure_state.external_trend.value
    prim_trend = TrendDirection(ext_trend_val)
    mtf_trends[prim_trend.value] = mtf_trends.get(prim_trend.value, 0) + 1

print("\n--- 4H MTF WITH UNIFIED ENUMS (First 2000 bars) ---")
print("MTF Trends seen (4H):", mtf_trends)
