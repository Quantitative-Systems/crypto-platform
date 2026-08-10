import unittest

from market_intelligence.raw_swing_engine import Candle
from market_intelligence.structure_builder_engine import EventType, StructureEvent
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

    def liquidity_sweep(self, idx, pool_type):
        return LiquidityEvent(
            timestamp=1_000_000 + idx * 60,
            event_type=LiquidityEventType.LIQUIDITY_SWEEP, pool_id=f"POOL_{idx}",
            pool_type=pool_type, liquidity_scope=LiquidityScope.EXTERNAL, price_level=100.0,
            direction="BULLISH_SWEEP" if pool_type in (LiquidityPoolType.SSL, LiquidityPoolType.EQL) else "BEARISH_SWEEP",
            candle_index=idx, swept_by_wick=True, body_closed_inside=True,
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

    def test_03_liquidity_sweep_alone_does_not_create_pullback(self):
        candles = [self.candle(i, 100+i, 102+i, 98+i, 101+i) for i in range(6)]
        liq = self.liquidity_state([self.liquidity_sweep(5, LiquidityPoolType.SSL)])
        state = PhaseEngine().process(candles, [self.bos(3, "BULLISH")], liquidity_state=liq)
        self.assertNotEqual(state.current_phase, MarketPhase.PULLBACK)

    def test_04_keyzone_created_alone_does_not_trigger_pullback(self):
        candles = [self.candle(i, 100, 102 + i, 98, 101 + i) for i in range(8)]
        structure = [self.bos(3, "BULLISH")]
        # KEYZONE_CREATED event at candle 6 must NOT trigger pullback without mitigation or counter-structure
        zones = self.keyzone_state([self.bullish_zone(6, KeyZoneEventType.KEYZONE_CREATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        self.assertEqual(state.current_phase, MarketPhase.EXPANSION)

    def test_05_keyzone_mitigated_triggers_pullback(self):
        candles = [self.candle(i, 100, 102 + i, 98, 101 + i) for i in range(8)]
        structure = [self.bos(3, "BULLISH")]
        # KEYZONE_MITIGATED event at candle 6 cleanly triggers pullback
        zones = self.keyzone_state([self.bullish_zone(6, KeyZoneEventType.KEYZONE_MITIGATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        self.assertEqual(state.current_phase, MarketPhase.PULLBACK)

    def test_06_continuation_requires_aligned_internal_shift(self):
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(10)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH"), self.internal_choch(9, "BULLISH")]
        zones = self.keyzone_state([
            self.bullish_zone(6, KeyZoneEventType.KEYZONE_MITIGATED),
        ])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        self.assertIn(MarketPhase.CONTINUATION, [event.new_phase for event in state.phase_history])

    def test_07_external_choch_creates_reversal(self):
        candles = [self.candle(i, 100, 103, 97, 101) for i in range(7)]
        state = PhaseEngine().process(candles, [self.bos(3, "BULLISH"), self.external_choch(6, "BEARISH")])
        self.assertEqual(state.current_phase, MarketPhase.REVERSAL)

    def test_08_bearish_external_bos(self):
        candles = [self.candle(i, 100-i, 102, 98-i, 99-i) for i in range(6)]
        state = PhaseEngine().process(candles, [self.bos(5, "BEARISH")])
        self.assertEqual(state.current_phase, MarketPhase.EXPANSION)
        self.assertEqual(state.current_trend.value, "BEARISH")

    def test_09_bearish_zone_is_directionally_recognised(self):
        candles = [self.candle(i, 100, 103, 97, 99) for i in range(8)]
        structure = [self.bos(3, "BEARISH")]
        zones = self.keyzone_state([self.bearish_zone(6, KeyZoneEventType.KEYZONE_MITIGATED)])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        self.assertIn(MarketPhase.PULLBACK, [event.new_phase for event in state.phase_history])

    def test_10_deterministic_replay(self):
        candles = [self.candle(i, 100+i, 103+i, 97+i, 102+i) for i in range(10)]
        structure = [self.bos(5, "BULLISH")]
        engine = PhaseEngine()
        first = engine.process(candles, structure)
        engine.reset()
        second = engine.process(candles, structure)
        self.assertEqual(first.current_phase, second.current_phase)
        self.assertEqual(first.current_trend, second.current_trend)

    def test_11_no_strategy_or_execution_fields(self):
        state = PhaseEngine().process([], [])
        forbidden = {"buy_signal", "sell_signal", "entry_price", "stop_loss", "take_profit", "position_size", "account_equity", "order_id", "broker"}
        for field in forbidden:
            self.assertFalse(hasattr(state, field), field)

    def test_12_non_chronological_candles_rejected(self):
        candles = [self.candle(0, 100, 102, 98, 101), self.candle(1, 100, 102, 98, 101)]
        candles[1] = Candle(timestamp=candles[0].timestamp - 1, open=100, high=102, low=98, close=101, volume=1000)
        with self.assertRaises(ValueError):
            PhaseEngine().process(candles, [])

    def test_13_invalid_parameters_rejected(self):
        with self.assertRaises(ValueError):
            PhaseEngine(atr_period=1)
        with self.assertRaises(ValueError):
            PhaseEngine(compression_ratio=0)
        with self.assertRaises(ValueError):
            PhaseEngine(range_lookback=2)

    def test_14_full_phase_transition_chain(self):
        # Accumulation -> Expansion -> Pullback -> Continuation
        candles = [self.candle(i, 100, 103 + i, 97, 101) for i in range(12)]
        structure = [self.bos(3, "BULLISH"), self.internal_choch(6, "BEARISH"), self.internal_choch(10, "BULLISH")]
        zones = self.keyzone_state([
            self.bullish_zone(6, KeyZoneEventType.KEYZONE_MITIGATED),
        ])
        state = PhaseEngine().process(candles, structure, keyzone_state=zones)
        phases = [event.new_phase for event in state.phase_history]
        self.assertIn(MarketPhase.EXPANSION, phases)
        self.assertIn(MarketPhase.PULLBACK, phases)
        self.assertIn(MarketPhase.CONTINUATION, phases)


if __name__ == "__main__":
    unittest.main()
