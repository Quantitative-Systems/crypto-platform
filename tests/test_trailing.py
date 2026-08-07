import unittest
from market_intelligence.primitives import (
    MarketStatePayload, StructureState, ClassifiedSwing, RawSwing,
    SwingType, SwingScope, SwingMagnitude, SwingCharacter, SwingStatus,
    TrendDirection
)
from trade_management.trailing import MTFTrailingEngine


class TestMTFTrailingEngine(unittest.TestCase):

    def _mock_classified_swing(self, price: float, swing_type: SwingType) -> ClassifiedSwing:
        raw = RawSwing(
            swing_id="SW1", timestamp=1000, price=price,
            swing_type=swing_type, candle_index=5, timeframe="1H",
            status=SwingStatus.CONFIRMED
        )
        return ClassifiedSwing(
            raw_swing=raw, scope=SwingScope.EXTERNAL,
            magnitude=SwingMagnitude.MAJOR, character=SwingCharacter.STRONG,
            status=SwingStatus.PROTECTED
        )

    def test_bullish_trailing_upward(self):
        low_swing = self._mock_classified_swing(105.0, SwingType.SWING_LOW)
        struct_state = StructureState(
            external_trend_seq=[],
            internal_trend_seq=[],
            protected_low=low_swing
        )
        payload = MarketStatePayload(
            symbol="BTC/USDT", timeframe="1H", timestamp=1000,
            current_price=110.0, current_candle=None, events=[], swings=[low_swing.raw_swing],
            structure_state=struct_state, liquidity_pools=[], keyzones=[],
            phase_state=None, trend_state=None, valuation_state=None,
            scorecard=None, metadata=None
        )

        update = MTFTrailingEngine.evaluate_trailing_stop(
            position_id="POS_1", direction=TrendDirection.BULLISH,
            current_sl=100.0, mtf_state=payload
        )

        self.assertTrue(update.should_update)
        self.assertEqual(update.new_stop_loss, 105.0)

    def test_bearish_trailing_downward(self):
        high_swing = self._mock_classified_swing(95.0, SwingType.SWING_HIGH)
        struct_state = StructureState(
            external_trend_seq=[],
            internal_trend_seq=[],
            protected_high=high_swing
        )
        payload = MarketStatePayload(
            symbol="BTC/USDT", timeframe="1H", timestamp=1000,
            current_price=90.0, current_candle=None, events=[], swings=[high_swing.raw_swing],
            structure_state=struct_state, liquidity_pools=[], keyzones=[],
            phase_state=None, trend_state=None, valuation_state=None,
            scorecard=None, metadata=None
        )

        update = MTFTrailingEngine.evaluate_trailing_stop(
            position_id="POS_2", direction=TrendDirection.BEARISH,
            current_sl=100.0, mtf_state=payload
        )

        self.assertTrue(update.should_update)
        self.assertEqual(update.new_stop_loss, 95.0)


if __name__ == "__main__":
    unittest.main()
