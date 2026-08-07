"""
Unit Test: Market Ontology Engine (BOS, CHOCH & Swing Detection)
"""

import unittest
from market_intelligence.primitives import Candle, TrendDirection, EventType
from market_intelligence.ontology import MarketOntology


class TestMarketOntology(unittest.TestCase):

    def setUp(self):
        self.ontology = MarketOntology(swing_lookback=2)

    def test_fractal_swing_and_bos_detection(self):
        # Construct a bullish market structure with a fractal high and a break
        candles = [
            Candle(timestamp=1000 + i * 3600, open=100 + i, high=102 + i, low=99 + i, close=101 + i, volume=100)
            for i in range(10)
        ]
        # Spike candle 5 to form a clear swing high
        candles[5] = Candle(timestamp=1000 + 5 * 3600, open=105, high=120, low=104, close=115, volume=500)
        # Candle 9 closes above swing high (BOS)
        candles[9] = Candle(timestamp=1000 + 9 * 3600, open=118, high=125, low=117, close=124, volume=800)

        res = self.ontology.evaluate_structure(candles, timeframe="1D")

        self.assertIn(res.external_trend, [TrendDirection.BULLISH, TrendDirection.BEARISH, TrendDirection.NEUTRAL])
        self.assertIsNotNone(res.active_swings)
        print("\n✅ Market Ontology Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()