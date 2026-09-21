"""
Engine 1 — Raw Swing Engine
Comprehensive deterministic test suite.
"""

import unittest

from market_intelligence.raw_swing_engine import (
    Candle,
    RawSwingConfig,
    RawSwingEngine,
    SwingType,
)


class TestRawSwingEngine(unittest.TestCase):

    @staticmethod
    def candle(
        i: int,
        high: float,
        low: float,
        close: float | None = None,
    ) -> Candle:
        if close is None:
            close = (high + low) / 2

        return Candle(
            timestamp=1_000 + i * 3_600,
            open=close,
            high=high,
            low=low,
            close=close,
            volume=1_000.0,
        )

    def test_01_insufficient_history_returns_empty(self):
        candles = [
            self.candle(i, 100 + i, 90 + i)
            for i in range(4)
        ]

        engine = RawSwingEngine(
            RawSwingConfig(left_bars=2, right_bars=2)
        )

        self.assertEqual(engine.detect(candles), [])

    def test_02_detects_swing_high(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 120, 95),
            self.candle(3, 105, 92),
            self.candle(4, 103, 91),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        highs = [
            swing for swing in swings
            if swing.swing_type == SwingType.HIGH
        ]

        self.assertEqual(len(highs), 1)
        self.assertEqual(highs[0].candle_index, 2)
        self.assertEqual(highs[0].price, 120)

    def test_03_detects_swing_low(self):
        candles = [
            self.candle(0, 110, 100),
            self.candle(1, 109, 99),
            self.candle(2, 105, 80),
            self.candle(3, 108, 98),
            self.candle(4, 110, 99),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        lows = [
            swing for swing in swings
            if swing.swing_type == SwingType.LOW
        ]

        self.assertEqual(len(lows), 1)
        self.assertEqual(lows[0].candle_index, 2)
        self.assertEqual(lows[0].price, 80)

    def test_04_confirmation_is_right_bars_after_extreme(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 120, 95),
            self.candle(3, 105, 92),
            self.candle(4, 103, 91),
        ]

        engine = RawSwingEngine(
            RawSwingConfig(left_bars=2, right_bars=2)
        )

        swings = engine.detect(candles)

        swing = swings[0]

        self.assertEqual(swing.candle_index, 2)
        self.assertEqual(swing.confirmation_index, 4)
        self.assertEqual(
            swing.confirmation_timestamp,
            candles[4].timestamp,
        )

    def test_05_equal_high_is_not_arbitrarily_selected(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 110, 91),
            self.candle(2, 120, 95),
            self.candle(3, 120, 92),
            self.candle(4, 105, 91),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        highs = [
            swing for swing in swings
            if swing.swing_type == SwingType.HIGH
        ]

        self.assertEqual(highs, [])

    def test_06_equal_low_is_not_arbitrarily_selected(self):
        candles = [
            self.candle(0, 110, 90),
            self.candle(1, 109, 80),
            self.candle(2, 105, 70),
            self.candle(3, 108, 70),
            self.candle(4, 110, 85),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        lows = [
            swing for swing in swings
            if swing.swing_type == SwingType.LOW
        ]

        self.assertEqual(lows, [])

    def test_07_multiple_swings_are_chronological(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 120, 91),
            self.candle(2, 105, 80),
            self.candle(3, 130, 90),
            self.candle(4, 110, 85),
            self.candle(5, 140, 95),
            self.candle(6, 120, 90),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        confirmation_indices = [
            swing.confirmation_index
            for swing in swings
        ]

        self.assertEqual(
            confirmation_indices,
            sorted(confirmation_indices),
        )

    def test_08_timeframe_is_preserved(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 120, 95),
            self.candle(3, 105, 92),
            self.candle(4, 103, 91),
        ]

        engine = RawSwingEngine(
            RawSwingConfig(
                left_bars=2,
                right_bars=2,
                timeframe="15M",
            )
        )

        swings = engine.detect(candles)

        self.assertEqual(swings[0].timeframe, "15M")

    def test_09_invalid_lookback_is_rejected(self):
        with self.assertRaises(ValueError):
            RawSwingConfig(left_bars=0)

        with self.assertRaises(ValueError):
            RawSwingConfig(right_bars=0)

    def test_10_invalid_candle_ohlc_is_rejected(self):
        candles = [
            Candle(
                timestamp=1,
                open=100,
                high=90,
                low=80,
                close=85,
                volume=100,
            )
        ]

        engine = RawSwingEngine()

        with self.assertRaises(ValueError):
            engine.detect(candles)

    def test_11_negative_volume_is_rejected(self):
        candles = [
            Candle(
                timestamp=1,
                open=90,
                high=100,
                low=80,
                close=90,
                volume=-1,
            )
        ]

        engine = RawSwingEngine()

        with self.assertRaises(ValueError):
            engine.detect(candles)

    def test_12_non_monotonic_timestamps_are_rejected(self):
        candles = [
            Candle(
                timestamp=2,
                open=90,
                high=100,
                low=80,
                close=90,
                volume=100,
            ),
            Candle(
                timestamp=1,
                open=90,
                high=100,
                low=80,
                close=90,
                volume=100,
            ),
        ]

        engine = RawSwingEngine()

        with self.assertRaises(ValueError):
            engine.detect(candles)

    def test_13_custom_fractal_configuration(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 102, 92),
            self.candle(3, 130, 95),
            self.candle(4, 110, 94),
            self.candle(5, 105, 93),
            self.candle(6, 104, 92),
        ]

        engine = RawSwingEngine(
            RawSwingConfig(left_bars=3, right_bars=3)
        )

        swings = engine.detect(candles)

        highs = [
            swing for swing in swings
            if swing.swing_type == SwingType.HIGH
        ]

        self.assertEqual(len(highs), 1)
        self.assertEqual(highs[0].candle_index, 3)
        self.assertEqual(highs[0].confirmation_index, 6)

    def test_14_swing_price_matches_actual_extreme(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 125, 75),
            self.candle(3, 105, 92),
            self.candle(4, 103, 91),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        high = next(
            swing for swing in swings
            if swing.swing_type == SwingType.HIGH
        )

        low = next(
            swing for swing in swings
            if swing.swing_type == SwingType.LOW
        )

        self.assertEqual(high.price, 125)
        self.assertEqual(low.price, 75)

    def test_15_no_strategy_concepts_exist_in_raw_output(self):
        candles = [
            self.candle(0, 100, 90),
            self.candle(1, 101, 91),
            self.candle(2, 120, 95),
            self.candle(3, 105, 92),
            self.candle(4, 103, 91),
        ]

        engine = RawSwingEngine()

        swings = engine.detect(candles)

        swing = swings[0]

        self.assertFalse(hasattr(swing, "bos"))
        self.assertFalse(hasattr(swing, "choch"))
        self.assertFalse(hasattr(swing, "trend"))
        self.assertFalse(hasattr(swing, "liquidity"))
        self.assertFalse(hasattr(swing, "keyzone"))


if __name__ == "__main__":
    unittest.main()
