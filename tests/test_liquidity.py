"""
Unit Test: Liquidity Engine (Equal Highs, Equal Lows & Sweep Detection)
"""

import unittest
from market_intelligence.primitives import Candle, LiquidityType, EventType
from market_intelligence.liquidity import LiquidityEngine


class TestLiquidityEngine(unittest.TestCase):

    def setUp(self):
        self.engine = LiquidityEngine()

    def test_eqh_and_sweep_detection(self):
        # Create candles forming Equal Highs at ~100.0
        candles = [
            Candle(timestamp=1000 + i * 100, open=95, high=100.0, low=90, close=96, volume=100)
            for i in range(12)
        ]
        # Second equal high at candle index 8
        candles[8] = Candle(timestamp=1000 + 800, open=95, high=100.05, low=91, close=97, volume=100)
        
        pools = self.engine.detect_pools(candles, timeframe="1H")
        self.assertTrue(len(pools) >= 1)

        # Candle 11 pierces 100.05 but closes below (Sweep)
        candles[11] = Candle(timestamp=1000 + 1100, open=98, high=101.5, low=95, close=99.0, volume=500)
        sweep = self.engine.detect_sweeps(candles, pools, timeframe="1H")

        self.assertIsNotNone(sweep)
        self.assertEqual(sweep.event_type, EventType.SWEEP)
        print("\n✅ Liquidity Engine Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()