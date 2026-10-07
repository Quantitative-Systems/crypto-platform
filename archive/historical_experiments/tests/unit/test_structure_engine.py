"""
Product 01 — Sub-System 1
Market Structure Engine Test Suite

The tests intentionally test behavior rather than merely checking
that functions return without exceptions.
"""

import unittest

from market_intelligence.primitives import (
    Candle,
    SwingType,
    SwingScope,
    SequenceLabel,
    TrendDirection,
    EventType,
    LiquiditySide,
    LiquidityPoolType,
)

from market_intelligence.structure_engine import (
    MarketStructureEngine,
)


class TestMarketStructureEngine(unittest.TestCase):

    # ============================================================
    # HELPERS
    # ============================================================

    def make_candle(
        self,
        i,
        high,
        low,
        close=None,
    ):
        if close is None:
            close = (high + low) / 2.0

        return Candle(
            timestamp=1000 + i * 3600,
            open=close,
            high=high,
            low=low,
            close=close,
            volume=1000.0,
        )

    # ============================================================
    # 01 — RAW SWINGS
    # ============================================================

    def test_01_raw_swing_confirmation(self):

        candles = [
            self.make_candle(0, 100, 90, 95),
            self.make_candle(1, 105, 91, 98),
            self.make_candle(2, 120, 95, 110),
            self.make_candle(3, 106, 92, 100),
            self.make_candle(4, 104, 90, 97),
        ]

        swings = MarketStructureEngine.detect_raw_swings(
            candles,
            lookback=2,
        )

        self.assertEqual(len(swings), 1)

        swing = swings[0]

        self.assertEqual(
            swing.swing_type,
            SwingType.SWING_HIGH,
        )

        self.assertEqual(
            swing.candle_index,
            2,
        )

        self.assertEqual(
            swing.confirmation_index,
            4,
        )

        self.assertEqual(
            swing.confirmation_timestamp,
            candles[4].timestamp,
        )

    # ============================================================
    # 02 — SEQUENCE LABELS
    # ============================================================

    def test_02_sequence_labels(self):

        raw = []

        prices = [
            (SwingType.SWING_HIGH, 100),
            (SwingType.SWING_LOW, 90),

            (SwingType.SWING_HIGH, 110),
            (SwingType.SWING_LOW, 95),

            (SwingType.SWING_HIGH, 120),
            (SwingType.SWING_LOW, 100),
        ]

        for i, (stype, price) in enumerate(prices):

            raw.append(
                __import__(
                    "market_intelligence.primitives",
                    fromlist=["RawSwing"],
                ).RawSwing(
                    swing_id=f"S{i}",
                    timestamp=i,
                    price=price,
                    swing_type=stype,
                    candle_index=i,
                    confirmation_timestamp=i + 2,
                    confirmation_index=i + 2,
                )
            )

        state = MarketStructureEngine.sequence_swings(raw)

        highs = [
            s
            for s in state.sequence_swings
            if s.raw_swing.swing_type == SwingType.SWING_HIGH
        ]

        lows = [
            s
            for s in state.sequence_swings
            if s.raw_swing.swing_type == SwingType.SWING_LOW
        ]

        self.assertEqual(
            highs[1].label,
            SequenceLabel.HH,
        )

        self.assertEqual(
            highs[2].label,
            SequenceLabel.HH,
        )

        self.assertEqual(
            lows[1].label,
            SequenceLabel.HL,
        )

        self.assertEqual(
            lows[2].label,
            SequenceLabel.HL,
        )

    # ============================================================
    # 03 — BULLISH TREND
    # ============================================================

    def test_03_bullish_trend(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 100,
                SwingType.SWING_HIGH,
                1, 3, 3,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L1", 2, 90,
                SwingType.SWING_LOW,
                2, 4, 4,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "H2", 3, 110,
                SwingType.SWING_HIGH,
                3, 5, 5,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L2", 4, 95,
                SwingType.SWING_LOW,
                4, 6, 6,
                scope=SwingScope.EXTERNAL,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        trend = MarketStructureEngine.determine_trend(
            state,
            SwingScope.EXTERNAL,
        )

        self.assertEqual(
            trend,
            TrendDirection.BULLISH,
        )

    # ============================================================
    # 04 — BEARISH TREND
    # ============================================================

    def test_04_bearish_trend(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 120,
                SwingType.SWING_HIGH,
                1, 3, 3,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L1", 2, 100,
                SwingType.SWING_LOW,
                2, 4, 4,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "H2", 3, 110,
                SwingType.SWING_HIGH,
                3, 5, 5,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L2", 4, 90,
                SwingType.SWING_LOW,
                4, 6, 6,
                scope=SwingScope.EXTERNAL,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        trend = MarketStructureEngine.determine_trend(
            state,
            SwingScope.EXTERNAL,
        )

        self.assertEqual(
            trend,
            TrendDirection.BEARISH,
        )

    # ============================================================
    # 05 — EQH
    # ============================================================

    def test_05_eqh_detection(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 100.00,
                SwingType.SWING_HIGH,
                1, 3, 3,
            ),
            RawSwing(
                "L1", 2, 90,
                SwingType.SWING_LOW,
                2, 4, 4,
            ),
            RawSwing(
                "H2", 3, 100.03,
                SwingType.SWING_HIGH,
                3, 5, 5,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        pools = (
            MarketStructureEngine
            .detect_eqh_eql_liquidity(
                state.sequence_swings,
                tolerance_pct=0.0005,
            )
        )

        self.assertTrue(
            any(
                pool.pool_type == LiquidityPoolType.EQH
                for pool in pools
            )
        )

    # ============================================================
    # 06 — EQL
    # ============================================================

    def test_06_eql_detection(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "L1", 1, 90.00,
                SwingType.SWING_LOW,
                1, 3, 3,
            ),
            RawSwing(
                "H1", 2, 100,
                SwingType.SWING_HIGH,
                2, 4, 4,
            ),
            RawSwing(
                "L2", 3, 90.03,
                SwingType.SWING_LOW,
                3, 5, 5,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        pools = (
            MarketStructureEngine
            .detect_eqh_eql_liquidity(
                state.sequence_swings,
                tolerance_pct=0.0005,
            )
        )

        self.assertTrue(
            any(
                pool.pool_type == LiquidityPoolType.EQL
                for pool in pools
            )
        )

    # ============================================================
    # 07 — LIQUIDITY SWEEP
    # ============================================================

    def test_07_bsl_sweep(self):

        candle = Candle(
            timestamp=100,
            open=99,
            high=105,
            low=97,
            close=99,
            volume=1000,
        )

        self.assertTrue(
            MarketStructureEngine.detect_liquidity_sweep(
                candle,
                100,
                LiquiditySide.BSL,
            )
        )

    # ============================================================
    # 08 — PROTECTED / WEAK BULLISH
    # ============================================================

    def test_08_bullish_structural_roles(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 100,
                SwingType.SWING_HIGH,
                1, 3, 3,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L1", 2, 90,
                SwingType.SWING_LOW,
                2, 4, 4,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "H2", 3, 110,
                SwingType.SWING_HIGH,
                3, 5, 5,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L2", 4, 95,
                SwingType.SWING_LOW,
                4, 6, 6,
                scope=SwingScope.EXTERNAL,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        trend = MarketStructureEngine.determine_trend(
            state,
            SwingScope.EXTERNAL,
        )

        (
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        ) = MarketStructureEngine.assign_structural_roles(
            state,
            trend,
        )

        self.assertIsNone(protected_high)

        self.assertIsNotNone(protected_low)

        self.assertIsNotNone(weak_high)

        self.assertTrue(
            protected_low.is_protected
        )

        self.assertTrue(
            protected_low.is_strong
        )

        self.assertTrue(
            weak_high.is_weak
        )

    # ============================================================
    # 09 — INTERNAL / EXTERNAL SEPARATION
    # ============================================================

    def test_09_internal_external_classification(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 100,
                SwingType.SWING_HIGH,
                1, 3, 3,
            ),
            RawSwing(
                "L1", 2, 90,
                SwingType.SWING_LOW,
                2, 4, 4,
            ),
            RawSwing(
                "H2", 3, 102,
                SwingType.SWING_HIGH,
                3, 5, 5,
            ),
            RawSwing(
                "L2", 4, 95,
                SwingType.SWING_LOW,
                4, 6, 6,
            ),
            RawSwing(
                "H3", 5, 120,
                SwingType.SWING_HIGH,
                5, 7, 7,
            ),
        ]

        result = (
            MarketStructureEngine
            .classify_hierarchical_structure(
                raw,
                external_span=1,
            )
        )

        self.assertTrue(
            any(
                swing.scope == SwingScope.INTERNAL
                for swing in result
            )
        )

        self.assertTrue(
            any(
                swing.scope == SwingScope.EXTERNAL
                for swing in result
            )
        )

    # ============================================================
    # 10 — MSS
    # ============================================================

    def test_10_bullish_to_bearish_mss(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 110,
                SwingType.SWING_HIGH,
                1, 3, 3,
                scope=SwingScope.EXTERNAL,
            ),

            RawSwing(
                "L1", 2, 100,
                SwingType.SWING_LOW,
                2, 4, 4,
                scope=SwingScope.EXTERNAL,
            ),

            RawSwing(
                "IH1", 3, 108,
                SwingType.SWING_HIGH,
                3, 5, 5,
                scope=SwingScope.INTERNAL,
            ),

            RawSwing(
                "IL1", 4, 103,
                SwingType.SWING_LOW,
                4, 6, 6,
                scope=SwingScope.INTERNAL,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        candle = Candle(
            timestamp=1000,
            open=104,
            high=105,
            low=101,
            close=102,
            volume=1000,
        )

        events = (
            MarketStructureEngine
            .evaluate_structure_events(
                candles=[candle],
                sequence_state=state,
                current_trend=TrendDirection.BULLISH,
            )
        )

        self.assertTrue(
            any(
                event.event_type == EventType.MSS
                for event in events
            )
        )

    # ============================================================
    # 11 — BEARISH INDUCEMENT
    # ============================================================

    def test_11_bearish_inducement(self):

        from market_intelligence.primitives import RawSwing

        raw = [
            RawSwing(
                "H1", 1, 110,
                SwingType.SWING_HIGH,
                1, 3, 3,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "L1", 2, 90,
                SwingType.SWING_LOW,
                2, 4, 4,
                scope=SwingScope.EXTERNAL,
            ),
            RawSwing(
                "IH1", 3, 105,
                SwingType.SWING_HIGH,
                3, 5, 5,
                scope=SwingScope.INTERNAL,
            ),
        ]

        state = MarketStructureEngine.sequence_swings(raw)

        candle = Candle(
            timestamp=1000,
            open=104,
            high=108,
            low=103,
            close=104,
            volume=1000,
        )

        events = (
            MarketStructureEngine
            .evaluate_structure_events(
                candles=[candle],
                sequence_state=state,
                current_trend=TrendDirection.BEARISH,
            )
        )

        self.assertTrue(
            any(
                event.event_type == EventType.INDUCEMENT
                for event in events
            )
        )

    # ============================================================
    # 12 — FULL PIPELINE
    # ============================================================

    def test_12_full_structure_pipeline(self):

        candles = []

        values = [
            (100, 90, 95),
            (105, 92, 100),
            (120, 95, 110),
            (108, 93, 100),
            (110, 94, 105),
            (125, 98, 115),
            (115, 100, 108),
            (130, 102, 120),
            (118, 101, 110),
        ]

        for i, (high, low, close) in enumerate(values):

            candles.append(
                self.make_candle(
                    i,
                    high,
                    low,
                    close,
                )
            )

        state = (
            MarketStructureEngine
            .process_full_structure(
                candles,
                symbol="BTC/USDT",
                timeframe="1H",
                lookback=1,
                external_span=1,
            )
        )

        self.assertIsNotNone(
            state.external_trend
        )

        self.assertIsNotNone(
            state.internal_trend
        )

        self.assertTrue(
            isinstance(
                state.external_swings,
                list,
            )
        )

        self.assertTrue(
            isinstance(
                state.internal_swings,
                list,
            )
        )


if __name__ == "__main__":
    unittest.main()
