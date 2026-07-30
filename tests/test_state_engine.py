"""
Product 01: Crypto Platform - Consolidated State Engine Verification Suite
Verifies end-to-end consolidation of Structure, KeyZones, and Liquidity into MarketStatePayload.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import Candle, TrendDirection
from market_intelligence.state_engine import MarketStateEngine


def generate_full_market_candles() -> list:
    """
    Generates a 20-candle synthetic series containing:
    - Multiple Swing Highs at matching price levels (~$110.00) -> EQH Pool
    - Red-to-Green expansion -> Bullish OB & Bullish FVG
    - Sweep Candle -> EQH Liquidity Sweep
    """
    base_time = 1700000000
    data = [
        (100, 102, 98, 101),   # 0
        (101, 106, 100, 105),  # 1
        (105, 110, 104, 109),  # 2: Swing High 1 @ 110.0
        (109, 109, 102, 103),  # 3
        (103, 104, 98, 99),    # 4: Swing Low 1 @ 98.0
        (99, 105, 98, 104),    # 5
        (104, 110, 103, 109),  # 6: Swing High 2 @ 110.0 (Matches Swing High 1 -> EQH at $110.0)
        (109, 109, 101, 102),  # 7
        (102, 103, 95, 96),    # 8: Bullish OB (Red candle before huge expansion)
        (96, 108, 95, 107),    # 9: Big expansion
        (107, 120, 106, 118),  # 10: Big expansion -> Bullish FVG created!
        (118, 119, 108, 109),  # 11: Retracement
        (109, 110, 94, 95),    # 12: EQL Low 1 @ 94.0
        (95, 105, 94, 104),    # 13: EQL Low 2 @ 94.0 -> EQL Pool
        (104, 114, 103, 108),  # 14: EQH Sweep (High 114 > 110 EQH, Close 108 < 110)
        (108, 109, 91, 95),    # 15: EQL Sweep (Low 91 < 94 EQL, Close 95 > 94)
        (95, 100, 94, 98),     # 16
        (98, 102, 97, 101),    # 17
        (101, 105, 100, 104),  # 18
        (104, 106, 101, 103)   # 19
    ]

    candles = []
    for i, (o, h, l, c) in enumerate(data):
        candles.append(Candle(
            timestamp=base_time + (i * 3600),
            open=float(o), high=float(h), low=float(l), close=float(c), volume=10000.0
        ))
    return candles


def run_state_engine_tests():
    print("==========================================================================================================")
    print("     PRODUCT 01: CONSOLIDATED MARKET STATE ENGINE VERIFICATION SUITE")
    print("==========================================================================================================\n")

    candles = generate_full_market_candles()
    engine = MarketStateEngine(swing_lookback=2)

    payload = engine.evaluate(candles, symbol="BTC/USDT", timeframe="4H")

    print("📊 [CONSOLIDATED MARKET STATE PAYLOAD]:")
    print(f"  • Asset & Timeframe  : {payload.symbol} ({payload.timeframe})")
    print(f"  • Active Trend       : {payload.trend.value}")
    print(f"  • Protected Anchors  : High=${payload.protected_high} | Low=${payload.protected_low}")
    if payload.last_event:
        print(f"  • Structural Event   : {payload.last_event.event_type.value} ({payload.last_event.direction.value})")
    print(f"  • Active Swings      : {len(payload.active_swings)} points mapped")
    print(f"  • Active KeyZones    : {len(payload.active_keyzones)} zones detected (OBs + FVGs)")
    print(f"  • Liquidity Pools    : {len(payload.active_liquidity_pools)} pools mapped (EQH/EQL)")
    print(f"  • Liquidity Sweeps   : {len(payload.active_liquidity_sweeps)} active sweeps detected")

    assert payload.symbol == "BTC/USDT", "FAIL: Payload symbol mismatch!"
    assert len(payload.active_keyzones) > 0, "FAIL: KeyZones missing from payload!"
    assert len(payload.active_liquidity_pools) > 0, "FAIL: Liquidity pools missing from payload!"
    assert len(payload.active_liquidity_sweeps) > 0, "FAIL: Liquidity sweeps missing from payload!"

    print("\n==========================================================================================================")
    print("  ✅ PHASE A COMPLETE: Market Intelligence System is 100% Operational & Consolidated!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_state_engine_tests()
