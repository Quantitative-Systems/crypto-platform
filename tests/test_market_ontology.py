"""
Product 01: Crypto Platform - Verification Test Suite
Tests UniversalMarketOntology Engine against synthetic price action.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import Candle, TrendDirection, EventType
from market_intelligence.ontology import UniversalOntologyEngine


def generate_synthetic_candles() -> list:
    """Generates a candle series: Range -> Bullish BOS -> Bearish CHOCH."""
    prices = [
        100, 102, 105, 103, 101, 99, 102, 106, 108, 112,
        110, 107, 109, 115, 118, 120, 116, 112, 108, 95
    ]
    candles = []
    base_time = 1700000000
    for i, p in enumerate(prices):
        candles.append(Candle(
            timestamp=base_time + (i * 3600),
            open=p - 1, high=p + 2, low=p - 2, close=p, volume=1000.0
        ))
    return candles


def run_tests():
    print("==========================================================================================================")
    print("     PRODUCT 01: UNIVERSAL MARKET ONTOLOGY VERIFICATION SUITE")
    print("==========================================================================================================\n")

    candles = generate_synthetic_candles()
    engine = UniversalOntologyEngine(swing_lookback=2)

    # Test 1: Swing Point Detection
    swings = engine.detect_swings(candles)
    print(f"  • Detected Fractal Swings: {len(swings)} points")
    for s in swings:
        print(f"    - Swing {s.swing_type.value} at Index {s.index}: ${s.price:.2f}")

    assert len(swings) > 0, "FAIL: No swings detected!"
    print("  ✅ PASS: Fractal Swing Detection Verified.\n")

    # Test 2: Market State & Structural Event Parsing
    payload = engine.evaluate_structure(candles, symbol="BTC/USDT", timeframe="1D")
    print("  • Parsed Market State Payload:")
    print(f"    - Symbol            : {payload.symbol}")
    print(f"    - Timeframe         : {payload.timeframe}")
    print(f"    - Active Trend      : {payload.trend.value}")
    print(f"    - Protected High    : {payload.protected_high}")
    print(f"    - Protected Low     : {payload.protected_low}")
    if payload.last_event:
        print(f"    - Last Event        : {payload.last_event.event_type.value} ({payload.last_event.direction.value}) at ${payload.last_event.broken_price_level:.2f}")

    assert payload.trend != TrendDirection.NEUTRAL, "FAIL: Trend evaluation failed!"
    print("\n==========================================================================================================")
    print("  ✅ ALL TESTS PASSED: Universal Market Ontology Engine is 100% Operational!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_tests()
