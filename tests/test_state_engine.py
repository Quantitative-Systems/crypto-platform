"""
Unit Test: Product 01 Market Intelligence Engine (V3.6 Architecture)
"""

import unittest
from market_intelligence.primitives import Candle, MarketStatePayload
from market_intelligence.state_engine import MarketStateEngine


class TestStateEngineV36(unittest.TestCase):

    def setUp(self):
        self.engine = MarketStateEngine(swing_lookback=2)
        self.candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0 + i, high=105.0 + i, low=99.0 + i, close=104.0 + i, volume=1000.0)
            for i in range(25)
        ]

    def test_v36_payload_generation(self):
        payload = self.engine.evaluate(self.candles, symbol="BTC/USDT", timeframe="1D")

        self.assertIsInstance(payload, MarketStatePayload)
        self.assertEqual(payload.symbol, "BTC/USDT")
        self.assertIsNotNone(payload.structure_state)
        self.assertIsNotNone(payload.trend_state)
        self.assertIsNotNone(payload.phase_state)
        self.assertTrue(payload.scorecard.overall_score > 0.0)
        self.assertEqual(payload.metadata.engine_version, "3.6.0-master")
        print("\n✅ Product 01 (V3.6 Pipeline) Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()