import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from market_intelligence.primitives import TrendDirection
from market_intelligence.phase_engine import MarketPhase

loader = WarehouseLoader()
htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
print(f"Loaded {len(htf_candles)} HTF candles")

coordinator = LanguageCoordinator(buffer_size=300)

trends_seen = {}
phases_seen = {}
biases_seen = {}

for i in range(15, len(htf_candles)):
    slice_c = htf_candles[max(0, i - 80):i + 1]
    htf_state = coordinator.run(slice_c, symbol="BTCUSDT", timeframe="1D")
    
    t = htf_state.trend_state
    p = htf_state.phase_state
    b = BiasClassifier.evaluate(htf_state)
    
    trends_seen[str(t)] = trends_seen.get(str(t), 0) + 1
    phases_seen[str(p)] = phases_seen.get(str(p), 0) + 1
    biases_seen[str(b)] = biases_seen.get(str(b), 0) + 1
    
    if i == 15 or i == 50:
        print(f"i={i}: trend={t} (type={type(t)}), phase={p} (type={type(p)}), bias={b}")
        print(f"  trend == TrendDirection.BULLISH: {t == TrendDirection.BULLISH}")
        print(f"  trend is TrendDirection.BULLISH: {t is TrendDirection.BULLISH}")
        print(f"  phase in (EXPANSION, PULLBACK, COMPRESSION): {p in (MarketPhase.EXPANSION, MarketPhase.PULLBACK, MarketPhase.COMPRESSION)}")

print("\nTrends seen:", trends_seen)
print("Phases seen:", phases_seen)
print("Biases seen:", biases_seen)
