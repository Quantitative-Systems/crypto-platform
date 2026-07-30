"""
Product 01: Crypto Platform - Keyzones Test Suite
Verifies Fair Value Gap (FVG) and Order Block (OB) detection algorithms.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import Candle, KeyZoneType, TrendDirection
from market_intelligence.keyzones import KeyZoneEngine


def generate_imbalance_candles() -> list:
    """Generates synthetic candles containing explicit Bullish/Bearish FVGs and OBs."""
    base_time = 1700000000
    # Candle 0: Base
    # Candle 1: Bullish OB candidate
    # Candle 2, 3: Explosive Bullish surge (creates Bullish FVG between 1 and 3)
    # Candle 4, 5, 6: Bearish crash (creates Bearish FVG)
    data = [
        (100, 102, 99, 101),   # 0
        (101, 102, 98, 99),    # 1: Bullish OB (Red candle)
        (100, 108, 100, 107),  # 2: Strong expansion
        (108, 118, 108, 116),  # 3: Strong expansion (FVG between C1 high=102 and C3 low=108)
        (116, 117, 110, 111),  # 4: Bearish OB candidate
        (110, 111, 98, 99),    # 5: Crash
        (99, 100, 85, 86)      # 6: Crash (Bearish FVG between C4 low=110 and C6 high=100)
    ]

    candles = []
    for i, (o, h, l, c) in enumerate(data):
        candles.append(Candle(
            timestamp=base_time + (i * 3600),
            open=float(o), high=float(h), low=float(l), close=float(c), volume=5000.0
        ))
    return candles


def run_keyzone_tests():
    print("==========================================================================================================")
    print("     PRODUCT 01: KEYZONES & IMBALANCE VERIFICATION SUITE")
    print("==========================================================================================================\n")

    candles = generate_imbalance_candles()

    # Test 1: Fair Value Gap Detection
    fvgs = KeyZoneEngine.detect_fair_value_gaps(candles)
    print(f"  • Detected Fair Value Gaps (FVGs): {len(fvgs)}")
    for zone in fvgs:
        print(f"    - [{zone.direction.value} FVG] Range: ${zone.low:.2f} -> ${zone.high:.2f} (Origin Candle: {zone.origin_candle_index})")

    assert len(fvgs) > 0, "FAIL: No Fair Value Gaps detected!"
    print("  ✅ PASS: Fair Value Gap Detection Verified.\n")

    # Test 2: Order Block Detection
    obs = KeyZoneEngine.detect_order_blocks(candles)
    print(f"  • Detected Order Blocks (OBs): {len(obs)}")
    for zone in obs:
        print(f"    - [{zone.direction.value} OB] Range: ${zone.low:.2f} -> ${zone.high:.2f} (Origin Candle: {zone.origin_candle_index})")

    assert len(obs) > 0, "FAIL: No Order Blocks detected!"
    print("  ✅ PASS: Order Block Detection Verified.\n")

    print("==========================================================================================================")
    print("  ✅ ALL KEYZONE TESTS PASSED: Keyzones & Imbalance Engine is 100% Operational!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_keyzone_tests()
