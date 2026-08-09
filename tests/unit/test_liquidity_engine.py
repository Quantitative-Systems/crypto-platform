"""
Quantitative Systems Platform — Crypto Platform Product
Product 01: Market Language | Engine 3 Unit Test Suite
Exhaustive verification of EQH/EQL pools, BSL/SSL structural liquidity,
liquidity sweeps, inducement detection, pool status transitions (ACTIVE -> SWEPT -> CONSUMED),
and zero-leakage isolation.
"""

import unittest
from market_intelligence.raw_swing_engine import Candle, RawSwing, SwingType, SwingStatus
from market_intelligence.structure_builder_engine import SequenceSwing, SequenceLabel, SwingScope, TrendDirection
from market_intelligence.liquidity_engine import (
    LiquidityEngine, LiquidityPoolType, LiquidityScope, PoolStatus, LiquidityEventType
)


class TestLiquidityEngineProduction(unittest.TestCase):

    def _raw_swing(self, index: int, price: float, swing_type: SwingType) -> RawSwing:
        return RawSwing(
            swing_id=f"SW_{index}", timestamp=1000 + index * 60, candle_index=index,
            price=price, swing_type=swing_type, confirmation_timestamp=1000 + (index + 2) * 60,
            confirmation_index=index + 2, timeframe="1H", status=SwingStatus.CONFIRMED
        )

    def _seq_swing(self, index: int, price: float, swing_type: SwingType, scope: SwingScope = SwingScope.EXTERNAL) -> SequenceSwing:
        raw = self._raw_swing(index, price, swing_type)
        return SequenceSwing(raw_swing=raw, label=SequenceLabel.UNKNOWN, scope=scope)

    def _candles(self, closes):
        return [
            Candle(timestamp=1000 + idx * 60, open=c - 1.0, high=c + 2.0, low=c - 2.0, close=c, volume=1000.0)
            for idx, c in enumerate(closes)
        ]

    def test_01_empty_state_returns_zero_pools(self):
        engine = LiquidityEngine()
        state = engine.process([], [])
        self.assertEqual(len(state.active_pools), 0)
        self.assertEqual(len(state.events), 0)

    def test_02_eqh_pool_detection(self):
        swings = [
            self._seq_swing(1, 100.00, SwingType.HIGH),
            self._seq_swing(2, 90.00, SwingType.LOW),
            self._seq_swing(3, 100.04, SwingType.HIGH)  # Within 0.05% tolerance
        ]
        engine = LiquidityEngine(eq_tolerance_pct=0.0005)
        state = engine.process(swings, self._candles([95] * 10))
        
        eqh_pools = [p for p in state.active_pools if p.pool_type == LiquidityPoolType.EQH]
        self.assertEqual(len(eqh_pools), 1)
        self.assertEqual(eqh_pools[0].status, PoolStatus.ACTIVE)

    def test_03_eql_pool_detection(self):
        swings = [
            self._seq_swing(1, 100.00, SwingType.HIGH),
            self._seq_swing(2, 90.00, SwingType.LOW),
            self._seq_swing(3, 110.00, SwingType.HIGH),
            self._seq_swing(4, 90.03, SwingType.LOW)  # Within 0.05% tolerance
        ]
        engine = LiquidityEngine(eq_tolerance_pct=0.0005)
        state = engine.process(swings, self._candles([95] * 10))
        
        eql_pools = [p for p in state.active_pools if p.pool_type == LiquidityPoolType.EQL]
        self.assertEqual(len(eql_pools), 1)

    def test_04_bsl_and_ssl_structural_pools(self):
        swings = [
            self._seq_swing(1, 120.00, SwingType.HIGH, SwingScope.EXTERNAL),
            self._seq_swing(2, 80.00, SwingType.LOW, SwingScope.EXTERNAL)
        ]
        engine = LiquidityEngine()
        state = engine.process(swings, self._candles([100] * 10))
        
        types = [p.pool_type for p in state.active_pools]
        self.assertIn(LiquidityPoolType.BSL, types)
        self.assertIn(LiquidityPoolType.SSL, types)

    def test_05_bsl_liquidity_sweep(self):
        swings = [
            self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL),
            self._seq_swing(2, 90.00, SwingType.LOW, SwingScope.EXTERNAL)
        ]
        candles = self._candles([95] * 10)
        # Candle 6 pierces 100.00 with High=105.00 but Closes at 98.00
        candles[6] = Candle(timestamp=1000 + 6 * 60, open=96.0, high=105.0, low=95.0, close=98.0, volume=1000.0)

        engine = LiquidityEngine()
        state = engine.process(swings, candles)

        self.assertEqual(len(state.events), 1)
        self.assertEqual(state.events[0].event_type, LiquidityEventType.LIQUIDITY_SWEEP)
        self.assertEqual(state.events[0].liquidity_scope, LiquidityScope.EXTERNAL)
        self.assertEqual(state.events[0].direction, "BEARISH_SWEEP")
        self.assertEqual(len(state.swept_pools), 1)

    def test_06_ssl_liquidity_sweep(self):
        swings = [
            self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL),
            self._seq_swing(2, 90.00, SwingType.LOW, SwingScope.EXTERNAL)
        ]
        candles = self._candles([95] * 10)
        # Candle 6 pierces 90.00 with Low=85.00 but Closes at 92.00
        candles[6] = Candle(timestamp=1000 + 6 * 60, open=94.0, high=96.0, low=85.0, close=92.0, volume=1000.0)

        engine = LiquidityEngine()
        state = engine.process(swings, candles)

        self.assertEqual(len(state.events), 1)
        self.assertEqual(state.events[0].event_type, LiquidityEventType.LIQUIDITY_SWEEP)
        self.assertEqual(state.events[0].direction, "BULLISH_SWEEP")

    def test_07_body_close_above_pool_is_consumed_not_swept(self):
        swings = [
            self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL)
        ]
        candles = self._candles([95] * 10)
        # Candle 5 closes at 105.00 (True breakout, body closed above boundary)
        candles[5] = Candle(timestamp=1000 + 5 * 60, open=98.0, high=108.0, low=97.0, close=105.0, volume=1000.0)

        engine = LiquidityEngine()
        state = engine.process(swings, candles)

        self.assertEqual(len(state.events), 0)  # No sweep event emitted
        self.assertEqual(len(state.swept_pools), 0)
        self.assertEqual(len(state.consumed_pools), 1)
        self.assertEqual(state.consumed_pools[0].status, PoolStatus.CONSUMED)

    def test_08_inducement_detection(self):
        swings = [
            self._seq_swing(1, 110.00, SwingType.HIGH, SwingScope.EXTERNAL),
            self._seq_swing(2, 90.00, SwingType.LOW, SwingScope.EXTERNAL),
            self._seq_swing(3, 95.00, SwingType.LOW, SwingScope.INTERNAL)
        ]
        candles = self._candles([98] * 10)
        # Candle 6 sweeps internal low 95.00 with Low=93.00, Close=96.00 in a BULLISH trend
        candles[6] = Candle(timestamp=1000 + 6 * 60, open=97.0, high=99.0, low=93.0, close=96.0, volume=1000.0)

        engine = LiquidityEngine()
        state = engine.process(swings, candles, external_trend=TrendDirection.BULLISH)

        inducements = [e for e in state.events if e.event_type == LiquidityEventType.INDUCEMENT]
        self.assertEqual(len(inducements), 1)

    def test_09_event_deduplication(self):
        swings = [self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL)]
        candles = self._candles([95] * 10)
        candles[5] = Candle(timestamp=1000 + 5 * 60, open=96.0, high=105.0, low=95.0, close=98.0, volume=1000.0)

        engine = LiquidityEngine()
        state1 = engine.process(swings, candles)
        self.assertEqual(len(state1.events), 1)

        # Processing same candles again must NOT emit duplicate event
        state2 = engine.process(swings, candles)
        self.assertEqual(len(state2.events), 0)

    def test_10_reset_allows_re_emission(self):
        swings = [self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL)]
        candles = self._candles([95] * 10)
        candles[5] = Candle(timestamp=1000 + 5 * 60, open=96.0, high=105.0, low=95.0, close=98.0, volume=1000.0)

        engine = LiquidityEngine()
        engine.process(swings, candles)
        engine.reset()

        state = engine.process(swings, candles)
        self.assertEqual(len(state.events), 1)

    def test_11_no_strategy_or_execution_leakage(self):
        swings = [self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL)]
        engine = LiquidityEngine()
        state = engine.process(swings, [])

        forbidden = ["buy_signal", "sell_signal", "stop_loss", "position_size", "order_block"]
        for field in forbidden:
            self.assertFalse(hasattr(state, field))

    def test_12_sweep_then_later_consumed_lifecycle(self):
        swings = [self._seq_swing(1, 100.00, SwingType.HIGH, SwingScope.EXTERNAL)]
        candles = self._candles([95] * 10)
        # Candle 5 sweeps 100.00 (High=105.00, Close=98.00)
        candles[5] = Candle(timestamp=1000 + 5 * 60, open=96.0, high=105.0, low=95.0, close=98.0, volume=1000.0)
        # Candle 7 body-closes above 100.00 (High=110.00, Close=103.00) -> Transitions SWEPT -> CONSUMED
        candles[7] = Candle(timestamp=1000 + 7 * 60, open=99.0, high=110.0, low=98.0, close=103.0, volume=1000.0)

        engine = LiquidityEngine()
        state = engine.process(swings, candles)

        # The earlier sweep event remains recorded in events history
        self.assertEqual(len(state.events), 1)
        self.assertEqual(state.events[0].event_type, LiquidityEventType.LIQUIDITY_SWEEP)
        # The pool status must end in consumed_pools array
        self.assertEqual(len(state.consumed_pools), 1)
        self.assertEqual(state.consumed_pools[0].status, PoolStatus.CONSUMED)
        self.assertEqual(state.consumed_pools[0].sweep_count, 1)


if __name__ == "__main__":
    unittest.main()
