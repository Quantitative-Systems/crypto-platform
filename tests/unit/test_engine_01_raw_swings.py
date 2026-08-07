"""
Exhaustive Unit Test Suite: Sub-Engine 01 Raw Swing Detection V4.3
"""

import unittest
from market_intelligence.primitives import Candle, SwingType, SwingStatus
from market_intelligence.engine_01_raw_swings import RawSwingEngine


class TestEngine01RawSwingsV43(unittest.TestCase):

    def setUp(self):
        self.engine = RawSwingEngine(swing_lookback=2, eq_tolerance_pct=0.001)

    def test_01_uuids_and_prev_next_linkage(self):
        """Verifies swing ID creation and relational linkage across swings."""
        candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0, high=101.0, low=99.0, close=100.5, volume=100.0)
            for i in range(12)
        ]
        candles[3] = Candle(timestamp=1000 + 3 * 3600, open=105.0, high=125.0, low=104.0, close=110.0, volume=500.0)
        candles[7] = Candle(timestamp=1000 + 7 * 3600, open=95.0, high=96.0, low=80.0, close=85.0, volume=500.0)

        swings = self.engine.detect_raw_swings(candles, timeframe="1H")

        self.assertEqual(len(swings), 2)
        self.assertIsNotNone(swings[0].swing_id)
        self.assertIsNotNone(swings[1].swing_id)
        self.assertIsNone(swings[0].prev_swing_id)
        self.assertEqual(swings[0].next_swing_id, swings[1].swing_id)
        self.assertEqual(swings[1].prev_swing_id, swings[0].swing_id)

    def test_02_eqh_cluster_detection(self):
        """Verifies multi-member Equal High (EQH) cluster grouping."""
        candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0, high=101.0, low=99.0, close=100.5, volume=100.0)
            for i in range(20)
        ]
        # Equal Highs at index 5 and index 12 (~135.0)
        candles[5] = Candle(timestamp=1000 + 5 * 3600, open=104.0, high=135.00, low=103.0, close=130.0, volume=5000.0)
        candles[12] = Candle(timestamp=1000 + 12 * 3600, open=110.0, high=135.02, low=109.0, close=128.0, volume=4000.0)

        swings = self.engine.detect_raw_swings(candles, timeframe="1H")
        eqh_swings = [s for s in swings if s.is_equal_extreme]

        self.assertTrue(len(eqh_swings) >= 2)
        self.assertEqual(eqh_swings[0].cluster_id, eqh_swings[1].cluster_id)
        self.assertEqual(eqh_swings[0].cluster_member_count, 2)

    def test_03_quality_and_displacement_metrics(self):
        """Verifies displacement percentage and quality score bounds."""
        candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0, high=101.0, low=99.0, close=100.5, volume=100.0)
            for i in range(10)
        ]
        candles[3] = Candle(timestamp=1000 + 3 * 3600, open=105.0, high=150.0, low=104.0, close=110.0, volume=500.0)

        swings = self.engine.detect_raw_swings(candles, timeframe="1H")
        self.assertTrue(len(swings) >= 1)
        self.assertTrue(swings[0].displacement_pct > 0.0)
        self.assertTrue(20.0 <= swings[0].quality_score <= 100.0)


if __name__ == "__main__":
    unittest.main()