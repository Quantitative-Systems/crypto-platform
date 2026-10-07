"""
Quantitative Systems Platform — Crypto Platform Product
Product 01: Market Language | Engine 4 Hardened Unit Test Suite
Exhaustive verification of Bullish/Bearish Order Blocks, Bullish/Bearish Fair Value Gaps,
KEYZONE_CREATED event emission, strict confirmation boundaries, Mitigation & Invalidation lifecycles,
liquidity-sweep strength scoring, and zero-leakage isolation.
"""

import unittest
from market_intelligence.raw_swing_engine import Candle
from market_intelligence.structure_builder_engine import StructureEvent, EventType
from market_intelligence.liquidity_engine import LiquidityState, LiquidityEvent, LiquidityEventType, LiquidityPoolType, LiquidityScope
from market_intelligence.keyzone_engine import (
    KeyZoneEngine, KeyZoneType, ZoneStatus, KeyZoneEventType
)


class TestKeyZoneEngineProduction(unittest.TestCase):

    def _mock_candle(self, idx: int, open_p: float, high: float, low: float, close: float) -> Candle:
        return Candle(
            timestamp=1000 + idx * 60,
            open=open_p, high=high, low=low, close=close, volume=1000.0
        )

    def _candles_from_closes(self, closes):
        return [
            self._mock_candle(idx, c - 1.0, c + 2.0, c - 2.0, c)
            for idx, c in enumerate(closes)
        ]

    def test_01_empty_state_returns_zero_zones(self):
        engine = KeyZoneEngine()
        state = engine.process([], [])
        self.assertEqual(len(state.active_zones), 0)
        self.assertEqual(len(state.events), 0)

    def test_02_bullish_order_block_detection(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 99.0),   # Candle 0
            self._mock_candle(1, 99.0, 101.0, 95.0, 96.0),    # Candle 1: Bearish origin candle
            self._mock_candle(2, 97.0, 110.0, 96.0, 108.0),   # Candle 2: Strong expansion candle
            self._mock_candle(3, 109.0, 115.0, 108.0, 114.0)  # Candle 3: BOS occurs
        ]
        bos_event = StructureEvent(
            timestamp=1000 + 3 * 60, event_type=EventType.EXTERNAL_BOS,
            price_level=102.0, broken_swing_id="SW_1", direction="BULLISH", candle_index=3
        )

        engine = KeyZoneEngine()
        state = engine.process(candles, [bos_event])

        obs = [z for z in state.active_zones if z.zone_type == KeyZoneType.BULLISH_OB]
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].high_boundary, 101.0)
        self.assertEqual(obs[0].low_boundary, 95.0)

    def test_03_bearish_order_block_detection(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),  # Candle 0
            self._mock_candle(1, 101.0, 105.0, 100.0, 104.0), # Candle 1: Bullish origin candle
            self._mock_candle(2, 103.0, 104.0, 90.0, 91.0),   # Candle 2: Bearish expansion surge
            self._mock_candle(3, 91.0, 92.0, 85.0, 86.0)     # Candle 3: BOS occurs
        ]
        bos_event = StructureEvent(
            timestamp=1000 + 3 * 60, event_type=EventType.EXTERNAL_BOS,
            price_level=98.0, broken_swing_id="SW_2", direction="BEARISH", candle_index=3
        )

        engine = KeyZoneEngine()
        state = engine.process(candles, [bos_event])

        obs = [z for z in state.active_zones if z.zone_type == KeyZoneType.BEARISH_OB]
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].high_boundary, 105.0)
        self.assertEqual(obs[0].low_boundary, 100.0)

    def test_04_bullish_fvg_detection(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),  # High = 102.0
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0), # Impulse
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0)  # Low = 105.0 (> 102.0)
        ]

        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        fvgs = [z for z in state.active_zones if z.zone_type == KeyZoneType.BULLISH_FVG]
        self.assertEqual(len(fvgs), 1)
        self.assertEqual(fvgs[0].high_boundary, 105.0)
        self.assertEqual(fvgs[0].low_boundary, 102.0)

    def test_05_bearish_fvg_detection(self):
        candles = [
            self._mock_candle(0, 100.0, 101.0, 95.0, 96.0),   # Low = 95.0
            self._mock_candle(1, 96.0, 96.0, 88.0, 89.0),     # Impulse
            self._mock_candle(2, 89.0, 92.0, 82.0, 83.0)     # High = 92.0 (< 95.0)
        ]

        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        fvgs = [z for z in state.active_zones if z.zone_type == KeyZoneType.BEARISH_FVG]
        self.assertEqual(len(fvgs), 1)
        self.assertEqual(fvgs[0].high_boundary, 95.0)
        self.assertEqual(fvgs[0].low_boundary, 92.0)

    def test_06_zone_mitigation_on_retest(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0), # FVG [102, 105] created at idx 2
            self._mock_candle(3, 113.0, 114.0, 103.0, 110.0)  # Retests 103.0 at idx 3 (mitigated)
        ]

        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        self.assertEqual(len(state.mitigated_zones), 1)
        self.assertEqual(state.mitigated_zones[0].status, ZoneStatus.MITIGATED)

    def test_07_zone_invalidation_on_body_break(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0), # FVG [102, 105]
            self._mock_candle(3, 108.0, 109.0, 98.0, 100.0)   # Closes at 100.0 (< 102.0 low boundary)
        ]

        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        self.assertEqual(len(state.invalidated_zones), 1)
        self.assertEqual(state.invalidated_zones[0].status, ZoneStatus.INVALIDATED)

    def test_08_no_ob_without_structure_break(self):
        candles = self._candles_from_closes([100, 98, 105, 104, 106])
        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        obs = [z for z in state.active_zones if z.zone_type in (KeyZoneType.BULLISH_OB, KeyZoneType.BEARISH_OB)]
        self.assertEqual(len(obs), 0)

    def test_09_event_deduplication(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0),
            self._mock_candle(3, 113.0, 114.0, 103.0, 110.0)
        ]
        engine = KeyZoneEngine()
        state1 = engine.process(candles, [])
        created_and_mitigated = len(state1.events)
        self.assertGreater(created_and_mitigated, 0)

        # Processing same candles again must NOT duplicate event
        state2 = engine.process(candles, [])
        self.assertEqual(len(state2.events), 0)

    def test_10_reset_allows_re_emission(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0),
            self._mock_candle(3, 113.0, 114.0, 103.0, 110.0)
        ]
        engine = KeyZoneEngine()
        engine.process(candles, [])
        engine.reset()

        state = engine.process(candles, [])
        self.assertGreater(len(state.events), 0)

    def test_11_no_strategy_or_execution_leakage(self):
        engine = KeyZoneEngine()
        state = engine.process([], [])

        forbidden = ["buy_signal", "sell_signal", "stop_loss", "position_size", "order_type"]
        for field in forbidden:
            self.assertFalse(hasattr(state, field))

    def test_12_no_future_data_leakage_causal_replay(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0) # FVG created at candle 2
        ]
        engine = KeyZoneEngine()
        # Processing only candles 0..1 must NOT detect the FVG until candle 2 is present
        state_early = engine.process(candles[:2], [])
        self.assertEqual(len(state_early.active_zones), 0)

        state_full = engine.process(candles, [])
        self.assertEqual(len(state_full.active_zones), 1)

    def test_13_deterministic_replay(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0)
        ]
        engine_a = KeyZoneEngine()
        engine_b = KeyZoneEngine()

        state_a = engine_a.process(candles, [])
        state_b = engine_b.process(candles, [])

        self.assertEqual(state_a.active_zones, state_b.active_zones)

    def test_14_strength_score_enhancement(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0)
        ]
        liq_event = LiquidityEvent(
            timestamp=1000 + 2 * 60, event_type=LiquidityEventType.LIQUIDITY_SWEEP,
            pool_id="SSL_SW_1", pool_type=LiquidityPoolType.SSL, liquidity_scope=LiquidityScope.EXTERNAL,
            price_level=98.0, direction="BULLISH_SWEEP", candle_index=2,
            swept_by_wick=True, body_closed_inside=True
        )
        liq_state = LiquidityState(active_pools=[], swept_pools=[], consumed_pools=[], events=[liq_event])

        engine = KeyZoneEngine()
        state = engine.process(candles, [], liquidity_state=liq_state)

        self.assertEqual(len(state.active_zones), 1)
        self.assertEqual(state.active_zones[0].strength_score, 1.5)

    def test_15_keyzone_created_event_emitted(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0)
        ]
        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        creation_events = [e for e in state.events if e.event_type == KeyZoneEventType.KEYZONE_CREATED]
        self.assertEqual(len(creation_events), 1)
        self.assertEqual(creation_events[0].zone_type, KeyZoneType.BULLISH_FVG)

    def test_16_internal_choch_does_not_create_order_block(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 99.0),
            self._mock_candle(1, 99.0, 101.0, 95.0, 96.0),
            self._mock_candle(2, 97.0, 110.0, 96.0, 108.0),
            self._mock_candle(3, 109.0, 115.0, 108.0, 114.0)
        ]
        choch_event = StructureEvent(
            timestamp=1000 + 3 * 60, event_type=EventType.INTERNAL_CHOCH,
            price_level=102.0, broken_swing_id="SW_1", direction="BULLISH_CHOCH", candle_index=3
        )

        engine = KeyZoneEngine()
        state = engine.process(candles, [choch_event])

        # INTERNAL_CHOCH must NOT trigger Order Block creation
        obs = [z for z in state.active_zones if z.zone_type == KeyZoneType.BULLISH_OB]
        self.assertEqual(len(obs), 0)

    def test_17_full_keyzone_event_lifecycle_sequence(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0), # FVG [102, 105] created
            self._mock_candle(3, 113.0, 114.0, 103.0, 110.0)  # FVG mitigated
        ]
        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        event_types = [e.event_type for e in state.events]
        self.assertIn(KeyZoneEventType.KEYZONE_CREATED, event_types)
        self.assertIn(KeyZoneEventType.KEYZONE_MITIGATED, event_types)

    def test_18_mitigation_then_invalidation_lifecycle(self):
        candles = [
            self._mock_candle(0, 100.0, 102.0, 98.0, 101.0),
            self._mock_candle(1, 101.0, 108.0, 101.0, 107.0),
            self._mock_candle(2, 107.0, 115.0, 105.0, 114.0), # FVG created at candle 2
            self._mock_candle(3, 113.0, 114.0, 103.0, 110.0), # Retests FVG (mitigated)
            self._mock_candle(4, 108.0, 109.0, 98.0, 100.0)   # Body closes below (invalidated)
        ]
        engine = KeyZoneEngine()
        state = engine.process(candles, [])

        self.assertEqual(len(state.invalidated_zones), 1)
        invalidated_zone = state.invalidated_zones[0]
        self.assertEqual(invalidated_zone.status, ZoneStatus.INVALIDATED)
        self.assertIsNotNone(invalidated_zone.mitigation_timestamp)


if __name__ == "__main__":
    unittest.main()
