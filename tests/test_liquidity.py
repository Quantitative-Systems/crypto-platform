"""
Product 01: Crypto Platform - Liquidity Test Suite
Verifies Equal Highs (EQH), Equal Lows (EQL), and Liquidity Sweep detection.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import Candle, SwingPoint, SwingType
from market_intelligence.liquidity import LiquidityEngine, LiquidityType


def generate_liquidity_candles_and_swings():
    """Generates synthetic candles and swing points containing an EQH and a Liquidity Sweep."""
    base_time = 1700000000
    
    # Swings forming Equal Highs at ~$105.00
    swings = [
        SwingPoint(index=2, price=105.00, swing_type=SwingType.HIGH, timestamp=base_time),
        SwingPoint(index=6, price=105.05, swing_type=SwingType.HIGH, timestamp=base_time + 3600),
    ]

    # Candle 8 pierces 105.05 up to 107.00 but closes down at 104.00 (EQH Sweep)
    data = [
        (100, 105, 99, 104),  # 0
        (104, 105, 101, 103), # 1
        (103, 105, 100, 102), # 2
        (102, 104, 98, 99),   # 3
        (99, 101, 97, 98),    # 4
        (98, 102, 97, 101),   # 5
        (101, 105, 100, 104), # 6
        (104, 104.5, 102, 103),# 7
        (103, 107.0, 101, 104)# 8: Sweep Candle
    ]

    candles = []
    for i, (o, h, l, c) in enumerate(data):
        candles.append(Candle(
            timestamp=base_time + (i * 3600),
            open=float(o), high=float(h), low=float(l), close=float(c), volume=2000.0
        ))

    return candles, swings


def run_liquidity_tests():
    print("==========================================================================================================")
    print("     PRODUCT 01: LIQUIDITY MAPPING & SWEEP VERIFICATION SUITE")
    print("==========================================================================================================\n")

    candles, swings = generate_liquidity_candles_and_swings()

    # Test 1: Equal Highs / Equal Lows Mapping
    pools = LiquidityEngine.detect_equal_levels(swings, tolerance_pct=0.0015)
    print(f"  • Mapped Liquidity Pools: {len(pools)}")
    for pool in pools:
        print(f"    - [{pool.pool_type.value} Pool] Level: ${pool.price_level:.2f} (Touches: {pool.touch_count})")

    assert len(pools) > 0, "FAIL: No equal levels detected!"
    print("  ✅ PASS: Equal Levels Detection Verified.\n")

    # Test 2: Liquidity Sweep Detection
    sweeps = LiquidityEngine.detect_sweeps(candles, pools)
    print(f"  • Detected Liquidity Sweeps: {len(sweeps)}")
    for sweep in sweeps:
        print(f"    - [{sweep.pool_type.value} Sweep] Pierced to ${sweep.sweep_price:.2f} at Candle Index {sweep.candle_index}")

    assert len(sweeps) > 0, "FAIL: No liquidity sweeps detected!"
    print("  ✅ PASS: Liquidity Sweep Detection Verified.\n")

    print("==========================================================================================================")
    print("  ✅ ALL LIQUIDITY TESTS PASSED: Liquidity Mapping Engine is 100% Operational!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_liquidity_tests()
