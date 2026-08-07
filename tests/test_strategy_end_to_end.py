"""
Unit Test: Strategy Pipeline Contract V2.1
"""

import unittest
from market_intelligence.primitives import Candle, ZoneType
from market_intelligence.state_engine import MarketStateEngine


class TestStrategyEndToEnd(unittest.TestCase):

    def setUp(self):
        self.engine = MarketStateEngine(swing_lookback=2)
        self.candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0 + i, high=105.0 + i, low=99.0 + i, close=104.0 + i, volume=1000.0)
            for i in range(15)
        ]

    def test_pipeline_execution(self):
        payload = self.engine.evaluate(self.candles, symbol="BTC/USDT", timeframe="1H")
        self.assertIsNotNone(payload)
        self.assertEqual(payload.symbol, "BTC/USDT")
        print("\n✅ End-to-End Strategy V2.1 Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()