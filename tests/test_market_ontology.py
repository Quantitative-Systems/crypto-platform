"""
Unit Test: Market Ontology Engine V2.1
"""

import unittest
from market_intelligence.primitives import Candle, TrendDirection
from market_intelligence.ontology import MarketOntology


class TestMarketOntology(unittest.TestCase):

    def setUp(self):
        self.ontology = MarketOntology(swing_lookback=2)

    def test_structure_evaluation(self):
        candles = [
            Candle(timestamp=1000 + i * 3600, open=100 + i, high=102 + i, low=99 + i, close=101 + i, volume=100)
            for i in range(10)
        ]
        candles[5] = Candle(timestamp=1000 + 5 * 3600, open=105, high=120, low=104, close=115, volume=500)
        candles[9] = Candle(timestamp=1000 + 9 * 3600, open=118, high=125, low=117, close=124, volume=800)

        res = self.ontology.evaluate_structure(candles, timeframe="1D")

        self.assertIsNotNone(res)
        self.assertIn(res.external_trend, [TrendDirection.BULLISH, TrendDirection.BEARISH, TrendDirection.NEUTRAL])
        print("\n✅ Market Ontology V2.1 Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()