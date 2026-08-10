import unittest

from market_intelligence.raw_swing_engine import Candle
from market_intelligence.structure_builder_engine import EventType, StructureEvent, TrendDirection
from market_intelligence.liquidity_engine import LiquidityEvent, LiquidityEventType, LiquidityPoolType, LiquidityScope, LiquidityState
from market_intelligence.keyzone_engine import KeyZoneEvent, KeyZoneEventType, KeyZoneState, KeyZoneType
from market_intelligence.phase_engine import PhaseEngine, MarketPhase, PhaseReason


class TestPhaseEngine(unittest.TestCase):

    def candle(self, idx, open_price, high, low, close):
        return Candle(
            timestamp=1_000_000 + idx * 60,
            open=open_price, high=high, low=low, close=close, volume=1000.0,
        )

    def bos(self, idx, direction="BULLISH"):
        return StructureEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=EventType.EXTERNAL_BOS,
            price_level=105.0, broken_swing_id=f"SW_{idx}",
            direction=direction, candle_index=idx, confirmation="BODY_CLOSE", structural_epoch=idx,
        )

    def internal_choch(self, idx, direction):
        return StructureEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=EventType.INTERNAL_CHOCH,
            price_level=103.0, broken_swing_id=f"I_SW_{idx}",
            direction=direction, candle_index=idx, confirmation="BODY_CLOSE", structural_epoch=idx,
        )

    def external_choch(self, idx, direction):
        return StructureEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=EventType.EXTERNAL_CHOCH,
            price_level=95.0, broken_swing_id=f"E_SW_{idx}",
            direction=direction, candle_index=idx, confirmation="BODY_CLOSE", structural_epoch=idx,
        )

    def bullish_zone(self, idx, event_type):
        return KeyZoneEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=event_type, zone_id=f"OB_B_{idx}",
            zone_type=KeyZoneType.BULLISH_OB, price_level=100.0,
            high_boundary=102.0, low_boundary=98.0, candle_index=idx,
        )

    def bearish_zone(self, idx, event_type):
        return KeyZoneEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=event_type, zone_id=f"OB_S_{idx}",
            zone_type=KeyZoneType.BEARISH_OB, price_level=100.0,
            high_boundary=102.0, low_boundary=98.0, candle_index=idx,
        )

    def liquidity_state(self, events):
        return LiquidityState(active_pools=[], swept_pools=[], consumed_pools=[], events=events)

    def keyzone_state(self, events):
        return KeyZoneState(active_zones=[], mitigated_zones=[], invalidated_zones=[], events=events)

    def test_01_empty_input(self):
        state = PhaseEngine().process([], [])
        self.assertEqual(state.current_phase, MarketPhase.ACCUMULATION)
        self.assertEqual(state.current_trend.value, "NEUTRAL")

    def test_02_external_bos_creates_expansion(self):
        candles = [self.candle(i, 100+i, 102+i, 98+i, 101+i) for i in range(6)]
        state = PhaseEngine().process(candles, [self.bos(5, "BULLISH")])
        self.assertEqual(state.current_phase, MarketPhase.EXPANSION)
        self.assertEqual(state.current_trend.value, "BULLISH")

    def test_03_counter_trend_internal_choch_triggers_pullback(self):
        candles = [self.candle(i, 100, 102 + i, 98, 101 + i) for i in range(8)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH")]
        state = PhaseEngine().process(candles, structure)
        self.assertEqual(state.current_phase, MarketPhase.PULLBACK)

    def test_04_internal_choch_does_not_cause_reversal(self):
        candles = [self.candle(i, 100, 102 + i, 98, 101 + i) for i in range(8)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH")]
        state = PhaseEngine().process(candles, structure)
        self.assertNotEqual(state.current_phase, MarketPhase.REVERSAL)
        self.assertEqual(state.current_trend.value, "BULLISH")  # Macro trend preserved!

    def test_05_continuation_requires_mitigated_zone_and_aligned_shift(self):
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(12)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH"), self.internal_choch(10, "BULLISH")]
        zones = self.keyzone_state([self.bullish_zone(8, KeyZoneEventType.KEYZONE_MITIGATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        phases = [e.new_phase for e in state.phase_history]
        self.assertIn(MarketPhase.CONTINUATION, phases)

    def test_06_external_choch_creates_reversal(self):
        candles = [self.candle(i, 100, 103, 97, 101) for i in range(7)]
        state = PhaseEngine().process(candles, [self.bos(3, "BULLISH"), self.external_choch(6, "BEARISH")])
        self.assertEqual(state.current_phase, MarketPhase.REVERSAL)
        self.assertEqual(state.current_trend.value, "BEARISH")

    def test_07_bearish_external_bos(self):
        candles = [self.candle(i, 100-i, 102, 98-i, 99-i) for i in range(6)]
        state = PhaseEngine().process(candles, [self.bos(5, "BEARISH")])
        self.assertEqual(state.current_phase, MarketPhase.EXPANSION)
        self.assertEqual(state.current_trend.value, "BEARISH")

    def test_08_bearish_counter_internal_choch_pullback(self):
        candles = [self.candle(i, 100, 103, 97, 99) for i in range(8)]
        structure = [self.bos(3, "BEARISH"), self.internal_choch(6, "BULLISH")]
        state = PhaseEngine().process(candles, structure)
        self.assertEqual(state.current_phase, MarketPhase.PULLBACK)

    def test_09_deterministic_replay(self):
        candles = [self.candle(i, 100+i, 103+i, 97+i, 102+i) for i in range(10)]
        structure = [self.bos(5, "BULLISH")]
        engine = PhaseEngine()
        first = engine.process(candles, structure)
        engine.reset()
        second = engine.process(candles, structure)
        self.assertEqual(first.current_phase, second.current_phase)
        self.assertEqual(first.current_trend, second.current_trend)

    def test_10_no_strategy_or_execution_fields(self):
        state = PhaseEngine().process([], [])
        forbidden = {"buy_signal", "sell_signal", "entry_price", "stop_loss", "take_profit", "position_size", "account_equity", "order_id", "broker"}
        for field in forbidden:
            self.assertFalse(hasattr(state, field), field)

    def test_11_non_chronological_candles_rejected(self):
        candles = [self.candle(0, 100, 102, 98, 101), self.candle(1, 100, 102, 98, 101)]
        candles[1] = Candle(timestamp=candles[0].timestamp - 1, open=100, high=102, low=98, close=101, volume=1000)
        with self.assertRaises(ValueError):
            PhaseEngine().process(candles, [])

    def test_12_invalid_parameters_rejected(self):
        with self.assertRaises(ValueError):
            PhaseEngine(atr_period=1)
        with self.assertRaises(ValueError):
            PhaseEngine(compression_ratio=0)

    def test_13_aligned_choch_without_keyzone_mitigation_remains_pullback(self):
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(12)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH"), self.internal_choch(10, "BULLISH")]
        state = PhaseEngine().process(candles, structure)  # No keyzones provided
        self.assertEqual(state.current_phase, MarketPhase.PULLBACK)

    def test_14_full_phase_transition_chain(self):
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(12)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH"), self.internal_choch(10, "BULLISH")]
        zones = self.keyzone_state([self.bullish_zone(8, KeyZoneEventType.KEYZONE_MITIGATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        phases = [e.new_phase for e in state.phase_history]
        self.assertIn(MarketPhase.EXPANSION, phases)
        self.assertIn(MarketPhase.PULLBACK, phases)
        self.assertIn(MarketPhase.CONTINUATION, phases)

    def test_15_aligned_choch_before_keyzone_mitigation_does_not_trigger_continuation(self):
        # Aligned shift at candle 5, but KeyZone mitigation happens LATER at candle 8
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(12)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(4, "BEARISH"), self.internal_choch(5, "BULLISH")]
        zones = self.keyzone_state([self.bullish_zone(8, KeyZoneEventType.KEYZONE_MITIGATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        # At candle 5, KeyZone mitigation has NOT occurred yet -> Must remain PULLBACK!
        phase_at_candle_5 = [e for e in state.events if e.candle_index == 5]
        self.assertEqual(len(phase_at_candle_5), 0)  # No transition to CONTINUATION at candle 5

    def test_16_reversal_evidence_captures_prior_parent_trend(self):
        candles = [self.candle(i, 100, 103, 97, 101) for i in range(8)]
        structure = [self.bos(3, "BULLISH"), self.external_choch(6, "BEARISH")]
        state = PhaseEngine().process(candles, structure)
        reversal_events = [e for e in state.events if e.new_phase == MarketPhase.REVERSAL]
        self.assertEqual(len(reversal_events), 1)
        # Evidence parent_trend MUST accurately record BULLISH (the trend BEFORE the reversal)
        self.assertEqual(reversal_events[0].evidence.parent_trend, TrendDirection.BULLISH)


if __name__ == "__main__":
    unittest.main()
