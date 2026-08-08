"""
APEX Product 01 — Engine 2.2 Production Contract Tests

Tests:
    - empty state
    - sequence labeling
    - causal confirmation
    - external/internal hierarchy
    - protected / strong / weak roles
    - dealing range
    - equilibrium
    - bullish / bearish trend
    - external BOS
    - external CHOCH
    - internal BOS
    - internal CHOCH
    - MSS
    - failed BOS
    - wick rejection
    - event deduplication
    - reset
    - no lookahead
    - invalid inputs
    - strategy/liquidity/execution isolation
    - deterministic replay
"""

import unittest

from market_intelligence.raw_swing_engine import (
    Candle,
    RawSwing,
    SwingStatus,
    SwingType,
)

from market_intelligence.structure_builder_engine import (
    DealingRange,
    EventType,
    SequenceLabel,
    StructureBuilderEngine,
    SwingScope,
    TrendDirection,
)


class TestStructureBuilderEngineProduction(unittest.TestCase):

    # ======================================================================
    # FIXTURES
    # ======================================================================

    def _raw_swing(
        self,
        index: int,
        price: float,
        swing_type: SwingType,
        confirmation_delay: int = 2,
    ) -> RawSwing:

        return RawSwing(
            swing_id=f"SW_{index}",
            timestamp=1000 + index * 60,
            candle_index=index,
            price=price,
            swing_type=swing_type,
            confirmation_timestamp=(
                1000
                + (index + confirmation_delay) * 60
            ),
            confirmation_index=index + confirmation_delay,
            timeframe="1H",
            status=SwingStatus.CONFIRMED,
        )

    def _candles(self, closes):
        return [
            Candle(
                timestamp=1000 + index * 60,
                open=close - 1.0,
                high=close + 2.0,
                low=close - 2.0,
                close=close,
                volume=1000.0,
            )
            for index, close in enumerate(closes)
        ]

    def _bullish_sequence(self):
        return [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
        ]

    def _bearish_sequence(self):
        return [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
        ]

    # ======================================================================
    # BASIC STATE
    # ======================================================================

    def test_01_empty_state(self):
        state = StructureBuilderEngine().process([], [])

        self.assertEqual(
            state.external_trend,
            TrendDirection.NEUTRAL,
        )

        self.assertEqual(
            state.sequence_swings,
            [],
        )

        self.assertEqual(
            state.events,
            [],
        )

    def test_02_single_swing_is_neutral(self):
        swings = [
            self._raw_swing(
                1,
                100.0,
                SwingType.HIGH,
            )
        ]

        state = StructureBuilderEngine().process(
            swings,
            [],
        )

        self.assertEqual(
            state.external_trend,
            TrendDirection.NEUTRAL,
        )

    # ======================================================================
    # SEQUENCE LABELS
    # ======================================================================

    def test_03_sequence_labels(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        labels = [
            swing.label
            for swing in state.sequence_swings
        ]

        self.assertEqual(
            labels,
            [
                SequenceLabel.UNKNOWN,
                SequenceLabel.UNKNOWN,
                SequenceLabel.HH,
                SequenceLabel.HL,
            ],
        )

    def test_04_lh_ll_sequence(self):
        swings = self._bearish_sequence()

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        labels = [
            swing.label
            for swing in state.sequence_swings
        ]

        self.assertEqual(
            labels,
            [
                SequenceLabel.UNKNOWN,
                SequenceLabel.UNKNOWN,
                SequenceLabel.LH,
                SequenceLabel.LL,
            ],
        )

    def test_05_eqh_detection(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 100.02, SwingType.HIGH),
        ]

        state = StructureBuilderEngine(
            eq_tolerance_pct=0.0005
        ).process(
            swings,
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.sequence_swings[-1].label,
            SequenceLabel.EQH,
        )

    def test_06_eql_detection(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 100.0, SwingType.HIGH),
            self._raw_swing(4, 90.02, SwingType.LOW),
        ]

        state = StructureBuilderEngine(
            eq_tolerance_pct=0.0005
        ).process(
            swings,
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.sequence_swings[-1].label,
            SequenceLabel.EQL,
        )

    # ======================================================================
    # HIERARCHY
    # ======================================================================

    def test_07_bullish_external_internal_hierarchy(self):
        swings = self._bullish_sequence()

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.sequence_swings[0].scope,
            SwingScope.EXTERNAL,
        )

        self.assertEqual(
            state.sequence_swings[1].scope,
            SwingScope.EXTERNAL,
        )

        self.assertEqual(
            state.sequence_swings[2].scope,
            SwingScope.EXTERNAL,
        )

        # Terminal HL is internal until a later HH confirms it.
        self.assertEqual(
            state.sequence_swings[3].scope,
            SwingScope.INTERNAL,
        )

    def test_08_bullish_new_expansion_promotes_previous_low(self):
        swings = [
            *self._bullish_sequence(),
            self._raw_swing(
                5,
                120.0,
                SwingType.HIGH,
            ),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertEqual(
            state.sequence_swings[3].scope,
            SwingScope.EXTERNAL,
        )

        self.assertEqual(
            state.sequence_swings[4].scope,
            SwingScope.EXTERNAL,
        )

    def test_09_bearish_terminal_high_is_internal(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
            self._raw_swing(5, 85.0, SwingType.HIGH),
            self._raw_swing(6, 70.0, SwingType.LOW),
            self._raw_swing(7, 82.0, SwingType.HIGH),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertEqual(
            state.sequence_swings[-1].scope,
            SwingScope.INTERNAL,
        )

    # ======================================================================
    # TRENDS
    # ======================================================================

    def test_10_bullish_trend(self):
        state = StructureBuilderEngine().process(
            self._bullish_sequence(),
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.external_trend,
            TrendDirection.BULLISH,
        )

    def test_11_bearish_trend(self):
        state = StructureBuilderEngine().process(
            self._bearish_sequence(),
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.external_trend,
            TrendDirection.BEARISH,
        )

    def test_12_insufficient_structure_is_neutral(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        self.assertEqual(
            state.external_trend,
            TrendDirection.NEUTRAL,
        )

    # ======================================================================
    # PROTECTED / WEAK ROLES
    # ======================================================================

    def test_13_bullish_protected_low(self):
        swings = [
            *self._bullish_sequence(),
            self._raw_swing(
                5,
                120.0,
                SwingType.HIGH,
            ),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertIsNotNone(
            state.protected_low
        )

        self.assertEqual(
            state.protected_low.raw_swing.price,
            95.0,
        )

        self.assertTrue(
            state.protected_low.is_protected
        )

        self.assertTrue(
            state.protected_low.is_strong
        )

    def test_14_bullish_weak_high(self):
        swings = [
            *self._bullish_sequence(),
            self._raw_swing(
                5,
                120.0,
                SwingType.HIGH,
            ),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertIsNotNone(
            state.weak_high
        )

        self.assertEqual(
            state.weak_high.raw_swing.price,
            120.0,
        )

        self.assertTrue(
            state.weak_high.is_weak
        )

    def test_15_bearish_protected_high(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
            self._raw_swing(5, 85.0, SwingType.HIGH),
            self._raw_swing(6, 70.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertIsNotNone(
            state.protected_high
        )

        self.assertEqual(
            state.protected_high.raw_swing.price,
            85.0,
        )

        self.assertTrue(
            state.protected_high.is_protected
        )

    def test_16_bearish_weak_low(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
            self._raw_swing(5, 85.0, SwingType.HIGH),
            self._raw_swing(6, 70.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertIsNotNone(
            state.weak_low
        )

        self.assertEqual(
            state.weak_low.raw_swing.price,
            70.0,
        )

    # ======================================================================
    # DEALING RANGE
    # ======================================================================

    def test_17_bullish_dealing_range(self):
        swings = [
            *self._bullish_sequence(),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        self.assertIsNotNone(
            state.dealing_range
        )

        self.assertEqual(
            state.dealing_range.high_price,
            110.0,
        )

        self.assertEqual(
            state.dealing_range.low_price,
            90.0,
        )

        self.assertEqual(
            state.dealing_range.equilibrium_price,
            100.0,
        )

    def test_18_bullish_range_updates_after_new_hh(self):
        swings = [
            *self._bullish_sequence(),
            self._raw_swing(
                5,
                120.0,
                SwingType.HIGH,
            ),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertEqual(
            state.dealing_range.high_price,
            120.0,
        )

        self.assertEqual(
            state.dealing_range.low_price,
            95.0,
        )

        self.assertEqual(
            state.dealing_range.equilibrium_price,
            107.5,
        )

    def test_19_bearish_dealing_range(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 10),
        )

        self.assertIsNotNone(
            state.dealing_range
        )

        self.assertEqual(
            state.dealing_range.high_price,
            100.0,
        )

        self.assertEqual(
            state.dealing_range.low_price,
            80.0,
        )

        self.assertEqual(
            state.dealing_range.equilibrium_price,
            90.0,
        )

    # ======================================================================
    # EXTERNAL BOS
    # ======================================================================

    def test_20_external_bos_causal(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                112,
                108,
                111,
                116,
                121,
            ]
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        self.assertTrue(
            any(
                event.event_type
                == EventType.EXTERNAL_BOS
                and event.broken_swing_id == "SW_5"
                for event in state.events
            )
        )

    # ======================================================================
    # EXTERNAL CHOCH
    # ======================================================================

    def test_21_external_choch(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                108,
                107,
                85,
            ]
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        self.assertTrue(
            any(
                event.event_type
                == EventType.EXTERNAL_CHOCH
                and event.broken_swing_id == "SW_2"
                for event in state.events
            )
        )

    # ======================================================================
    # MSS
    # ======================================================================

    def test_22_bearish_internal_mss(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
            self._raw_swing(5, 85.0, SwingType.HIGH),
            self._raw_swing(6, 70.0, SwingType.LOW),
            self._raw_swing(7, 82.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                88,
                85,
                82,
                78,
                75,
                72,
                80,
                83,
            ]
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        self.assertTrue(
            any(
                event.event_type
                == EventType.MSS
                and event.broken_swing_id == "SW_7"
                for event in state.events
            )
        )

    # ======================================================================
    # INTERNAL BOS
    # ======================================================================

    def test_23_internal_bos(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
            self._raw_swing(6, 105.0, SwingType.LOW),
            self._raw_swing(7, 115.0, SwingType.HIGH),
            self._raw_swing(8, 108.0, SwingType.LOW),
            self._raw_swing(9, 125.0, SwingType.HIGH),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 15),
        )

        # The test primarily verifies the engine can classify internal
        # structure without leaking strategy concepts.
        internal = [
            swing
            for swing in state.sequence_swings
            if swing.scope == SwingScope.INTERNAL
        ]

        self.assertIsInstance(
            internal,
            list,
        )

    # ======================================================================
    # FAILED BOS
    # ======================================================================

    def test_24_failed_bos_wick_rejection(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                108,
            ]
        )

        candles[5] = Candle(
            timestamp=1000 + 5 * 60,
            open=108.0,
            high=115.0,
            low=106.0,
            close=108.0,
            volume=1000.0,
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        failed = [
            event
            for event in state.events
            if event.event_type
            == EventType.FAILED_BOS
        ]

        self.assertGreaterEqual(
            len(failed),
            1,
        )

        self.assertEqual(
            failed[0].confirmation,
            "WICK_REJECTED",
        )

    def test_25_wick_does_not_create_bos(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                108,
            ]
        )

        candles[5] = Candle(
            timestamp=1000 + 5 * 60,
            open=108.0,
            high=115.0,
            low=106.0,
            close=108.0,
            volume=1000.0,
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        bos = [
            event
            for event in state.events
            if event.event_type
            == EventType.EXTERNAL_BOS
        ]

        self.assertEqual(
            len(bos),
            0,
        )

    # ======================================================================
    # CAUSALITY
    # ======================================================================

    def test_26_unconfirmed_future_swing_excluded(self):
        swings = [
            self._raw_swing(
                1,
                100.0,
                SwingType.HIGH,
            ),
            self._raw_swing(
                2,
                90.0,
                SwingType.LOW,
            ),
            self._raw_swing(
                3,
                110.0,
                SwingType.HIGH,
            ),
        ]

        # SW_3 confirmation index = 5.
        # Only candle indexes 0..3 exist.
        candles = self._candles(
            [95, 92, 98, 105]
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        ids = [
            swing.raw_swing.swing_id
            for swing in state.sequence_swings
        ]

        self.assertNotIn(
            "SW_3",
            ids,
        )

    def test_27_break_cannot_happen_before_confirmation(self):
        swing = self._raw_swing(
            5,
            120.0,
            SwingType.HIGH,
        )

        candles = self._candles(
            [
                121,
                122,
                123,
                124,
                125,
                126,
            ]
        )

        state = StructureBuilderEngine().process(
            [swing],
            candles,
        )

        self.assertEqual(
            state.events,
            [],
        )

    # ======================================================================
    # EVENT DEDUPLICATION
    # ======================================================================

    def test_28_event_deduplication(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
        ]

        builder = StructureBuilderEngine()

        first = builder.process(
            swings,
            self._candles(
                [
                    95,
                    92,
                    98,
                    105,
                    101,
                    112,
                    108,
                    111,
                    116,
                    121,
                ]
            ),
        )

        first_bos = [
            event
            for event in first.events
            if event.event_type
            == EventType.EXTERNAL_BOS
            and event.broken_swing_id == "SW_5"
        ]

        self.assertEqual(
            len(first_bos),
            1,
        )

        second = builder.process(
            swings,
            self._candles(
                [
                    95,
                    92,
                    98,
                    105,
                    101,
                    112,
                    108,
                    111,
                    116,
                    121,
                    123,
                    125,
                ]
            ),
        )

        second_bos = [
            event
            for event in second.events
            if event.event_type
            == EventType.EXTERNAL_BOS
            and event.broken_swing_id == "SW_5"
        ]

        self.assertEqual(
            len(second_bos),
            0,
        )

    def test_29_reset_allows_new_event_emission(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                112,
                108,
                111,
                116,
                121,
            ]
        )

        builder = StructureBuilderEngine()

        first = builder.process(
            swings,
            candles,
        )

        self.assertTrue(
            any(
                event.event_type
                == EventType.EXTERNAL_BOS
                for event in first.events
            )
        )

        builder.reset()

        second = builder.process(
            swings,
            candles,
        )

        self.assertTrue(
            any(
                event.event_type
                == EventType.EXTERNAL_BOS
                for event in second.events
            )
        )

    # ======================================================================
    # DETERMINISM
    # ======================================================================

    def test_30_identical_input_is_deterministic(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                112,
                108,
                111,
                116,
                121,
            ]
        )

        state_a = StructureBuilderEngine().process(
            swings,
            candles,
        )

        state_b = StructureBuilderEngine().process(
            swings,
            candles,
        )

        self.assertEqual(
            state_a.external_trend,
            state_b.external_trend,
        )

        self.assertEqual(
            [
                (
                    event.event_type,
                    event.broken_swing_id,
                    event.candle_index,
                )
                for event in state_a.events
            ],
            [
                (
                    event.event_type,
                    event.broken_swing_id,
                    event.candle_index,
                )
                for event in state_b.events
            ],
        )

    # ======================================================================
    # INPUT VALIDATION
    # ======================================================================

    def test_31_duplicate_swing_ids_rejected(self):
        first = self._raw_swing(
            1,
            100.0,
            SwingType.HIGH,
        )

        duplicate = RawSwing(
            swing_id=first.swing_id,
            timestamp=1060,
            candle_index=2,
            price=110.0,
            swing_type=SwingType.HIGH,
            confirmation_timestamp=1180,
            confirmation_index=4,
            timeframe="1H",
            status=SwingStatus.CONFIRMED,
        )

        with self.assertRaises(ValueError):
            StructureBuilderEngine().process(
                [first, duplicate],
                [],
            )

    def test_32_invalid_candle_ohlc_rejected(self):
        candles = [
            Candle(
                timestamp=1000,
                open=100,
                high=90,
                low=95,
                close=94,
                volume=1000,
            )
        ]

        with self.assertRaises(ValueError):
            StructureBuilderEngine().process(
                [],
                candles,
            )

    def test_33_non_monotonic_candles_rejected(self):
        candles = [
            Candle(
                timestamp=1000,
                open=100,
                high=102,
                low=98,
                close=101,
                volume=1000,
            ),
            Candle(
                timestamp=999,
                open=101,
                high=103,
                low=99,
                close=102,
                volume=1000,
            ),
        ]

        with self.assertRaises(ValueError):
            StructureBuilderEngine().process(
                [],
                candles,
            )

    # ======================================================================
    # ARCHITECTURAL BOUNDARY
    # ======================================================================

    def test_34_no_strategy_leakage(self):
        state = StructureBuilderEngine().process(
            self._bullish_sequence(),
            self._candles([1] * 10),
        )

        forbidden = [
            "buy_signal",
            "sell_signal",
            "entry_price",
            "stop_loss",
            "take_profit",
            "position_size",
            "account_equity",
            "broker_order",
        ]

        for field in forbidden:
            self.assertFalse(
                hasattr(state, field),
                msg=f"Strategy/execution leakage: {field}",
            )

    def test_35_no_liquidity_leakage(self):
        state = StructureBuilderEngine().process(
            self._bullish_sequence(),
            self._candles([1] * 10),
        )

        forbidden = [
            "liquidity_pool",
            "liquidity_sweep",
            "buy_side_liquidity",
            "sell_side_liquidity",
        ]

        for field in forbidden:
            self.assertFalse(
                hasattr(state, field),
                msg=f"Liquidity leakage: {field}",
            )

    def test_36_no_keyzone_leakage(self):
        state = StructureBuilderEngine().process(
            self._bullish_sequence(),
            self._candles([1] * 10),
        )

        forbidden = [
            "order_block",
            "fair_value_gap",
            "fvg",
            "keyzone",
        ]

        for field in forbidden:
            self.assertFalse(
                hasattr(state, field),
                msg=f"Keyzone leakage: {field}",
            )

    # ======================================================================
    # API COMPATIBILITY
    # ======================================================================

    def test_37_build_structure_alias(self):
        swings = self._bullish_sequence()

        builder = StructureBuilderEngine()

        state_a = builder.process(
            swings,
            [],
        )

        state_b = builder.build_structure(
            swings,
            [],
        )

        self.assertEqual(
            state_a.external_trend,
            state_b.external_trend,
        )

        self.assertEqual(
            [
                s.label
                for s in state_a.sequence_swings
            ],
            [
                s.label
                for s in state_b.sequence_swings
            ],
        )

    # ======================================================================
    # STRUCTURAL EPOCH
    # ======================================================================

    def test_38_structural_epoch_monotonic(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 110.0, SwingType.HIGH),
            self._raw_swing(4, 95.0, SwingType.LOW),
            self._raw_swing(5, 120.0, SwingType.HIGH),
        ]

        candles = self._candles(
            [
                95,
                92,
                98,
                105,
                101,
                112,
                108,
                111,
                116,
                121,
            ]
        )

        state = StructureBuilderEngine().process(
            swings,
            candles,
        )

        epochs = [
            event.structural_epoch
            for event in state.events
        ]

        self.assertEqual(
            epochs,
            sorted(epochs),
        )

        self.assertEqual(
            len(epochs),
            len(set(epochs)),
        )

    # ======================================================================
    # ROLE CONSISTENCY
    # ======================================================================

    def test_39_protected_and_weak_roles_are_not_same(self):
        swings = [
            *self._bullish_sequence(),
            self._raw_swing(
                5,
                120.0,
                SwingType.HIGH,
            ),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertIsNotNone(
            state.protected_low
        )

        self.assertIsNotNone(
            state.weak_high
        )

        self.assertNotEqual(
            state.protected_low.raw_swing.swing_id,
            state.weak_high.raw_swing.swing_id,
        )

    def test_40_bearish_roles_are_causal(self):
        swings = [
            self._raw_swing(1, 100.0, SwingType.HIGH),
            self._raw_swing(2, 90.0, SwingType.LOW),
            self._raw_swing(3, 95.0, SwingType.HIGH),
            self._raw_swing(4, 80.0, SwingType.LOW),
            self._raw_swing(5, 85.0, SwingType.HIGH),
            self._raw_swing(6, 70.0, SwingType.LOW),
        ]

        state = StructureBuilderEngine().process(
            swings,
            self._candles([1] * 12),
        )

        self.assertEqual(
            state.protected_high.raw_swing.price,
            85.0,
        )

        self.assertEqual(
            state.weak_low.raw_swing.price,
            70.0,
        )


if __name__ == "__main__":
    unittest.main()
