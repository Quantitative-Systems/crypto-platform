"""
Unit Test: Slice 2 Decision Engines (HTF Bias, MTF Setup, LTF Trigger V2.1)
"""

import unittest
from market_intelligence.primitives import Candle, TrendDirection, MarketPhase
from market_intelligence.state_engine import MarketStateEngine
from strategy.htf_bias import HTFBiasEngine
from strategy.mtf_setup import MTFSetupEngine


class TestDecisionLayerV2(unittest.TestCase):

    def setUp(self):
        self.state_engine = MarketStateEngine(swing_lookback=2)
        # Construct synthetic candle series with clear trend movement
        self.candles = [
            Candle(timestamp=1000 + i * 3600, open=100.0 + i, high=105.0 + i, low=99.0 + i, close=104.0 + i, volume=1000.0)
            for i in range(15)
        ]

    def test_decision_chain(self):
        payload = self.state_engine.evaluate(self.candles, symbol="BTC/USDT", timeframe="1D")
        
        # 1. HTF Bias Evaluation
        htf_res = HTFBiasEngine.evaluate_bias(payload)
        self.assertTrue(htf_res.is_valid)
        self.assertIsNotNone(htf_res.target_tp_price)

        # 2. MTF Setup Evaluation
        mtf_res = MTFSetupEngine.evaluate_setup(htf_res.bias, payload)
        self.assertTrue(mtf_res.is_aligned)

        print("\n✅ Slice 2 Decision Layer V2.1 Unit Test PASSED!")


if __name__ == "__main__":
    unittest.main()