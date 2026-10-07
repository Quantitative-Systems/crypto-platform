"""Unit tests for the FractalStateEngine and its components."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructuralBreak,
    StructuralBreakType,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from market_model.fractal_state_engine import (
    ConditionalHypothesisEngine,
    CrossSetCoherenceTracker,
    FractalAlignment,
    FractalBias,
    FractalStateEngine,
    FractalStateNode,
    TimeframeRank,
    TimeframeState,
    TIMEFRAME_LABEL_TO_RANK,
    TIMEFRAME_SETS,
)


def _make_state(
    trend: TrendDirection = TrendDirection.BULLISH,
    phase: MarketPhaseType = MarketPhaseType.PULLBACK,
    pd_zone: str = "DISCOUNT",
    breaks: list = None,
    weak_high: float = None,
    weak_low: float = None,
    close_price: float = 100.0,
) -> MarketState:
    """Create a minimal MarketState for testing."""
    struct = StructureSnapshot(
        external_trend=trend,
        internal_trend=trend,
        weak_high=weak_high,
        weak_low=weak_low,
        last_major_low=SwingPoint(timestamp_ms=0, price=90.0, is_high=False),
        last_major_high=SwingPoint(timestamp_ms=0, price=110.0, is_high=True),
    )
    if breaks:
        struct.recent_breaks = breaks

    zones = ZonesSnapshot(premium_discount_zone=pd_zone)
    phase_snap = PhaseSnapshot(current_phase=phase)

    return MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1000000,
        timeframe="1d",
        close_price=close_price,
        structure=struct,
        zones=zones,
        phase=phase_snap,
    )


def _make_tf_state(
    label: str,
    trend: TrendDirection = TrendDirection.BULLISH,
    phase: MarketPhaseType = MarketPhaseType.PULLBACK,
    pd_zone: str = "DISCOUNT",
    breaks: list = None,
    weak_high: float = None,
    weak_low: float = None,
) -> TimeframeState:
    """Create a TimeframeState with embedded MarketState."""
    rank = TIMEFRAME_LABEL_TO_RANK.get(label, TimeframeRank.TF_1D)
    state = _make_state(trend=trend, phase=phase, pd_zone=pd_zone, breaks=breaks,
                        weak_high=weak_high, weak_low=weak_low)
    return TimeframeState(label=label, rank=rank, state=state, last_computed_ts=1000000)


class TestTimeframeRank(unittest.TestCase):
    """Tests for the TimeframeRank hierarchy."""

    def test_rank_ordering(self):
        """Higher rank = slower timeframe."""
        self.assertGreater(TimeframeRank.TF_1M, TimeframeRank.TF_1W)
        self.assertGreater(TimeframeRank.TF_1W, TimeframeRank.TF_1D)
        self.assertGreater(TimeframeRank.TF_1D, TimeframeRank.TF_4H)
        self.assertGreater(TimeframeRank.TF_4H, TimeframeRank.TF_1H)
        self.assertGreater(TimeframeRank.TF_1H, TimeframeRank.TF_15M)
        self.assertGreater(TimeframeRank.TF_15M, TimeframeRank.TF_3M)

    def test_label_to_rank_mapping(self):
        """All 7 timeframes are mapped."""
        self.assertEqual(len(TIMEFRAME_LABEL_TO_RANK), 7)
        self.assertEqual(TIMEFRAME_LABEL_TO_RANK["1M"], TimeframeRank.TF_1M)
        self.assertEqual(TIMEFRAME_LABEL_TO_RANK["3m"], TimeframeRank.TF_3M)


class TestTimeframeState(unittest.TestCase):
    """Tests for TimeframeState properties."""

    def test_trend_property(self):
        ts = _make_tf_state("1d", trend=TrendDirection.BULLISH)
        self.assertEqual(ts.trend, TrendDirection.BULLISH)
        self.assertTrue(ts.is_bullish)
        self.assertFalse(ts.is_bearish)
        self.assertTrue(ts.is_directional)

    def test_neutral_not_directional(self):
        ts = TimeframeState(label="1d", rank=TimeframeRank.TF_1D)
        self.assertEqual(ts.trend, TrendDirection.NEUTRAL)
        self.assertFalse(ts.is_directional)

    def test_bearish_properties(self):
        ts = _make_tf_state("4h", trend=TrendDirection.BEARISH)
        self.assertTrue(ts.is_bearish)
        self.assertFalse(ts.is_bullish)
        self.assertTrue(ts.is_directional)


class TestFractalStateNode(unittest.TestCase):
    """Tests for FractalStateNode alignment computation."""

    def test_fully_aligned(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH),
        }
        self.assertEqual(
            node.get_alignment_for_set("SET_2"),
            FractalAlignment.FULLY_ALIGNED,
        )

    def test_htf_mtf_aligned(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BEARISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BEARISH),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH),
        }
        self.assertEqual(
            node.get_alignment_for_set("SET_2"),
            FractalAlignment.HTF_MTF_ALIGNED,
        )

    def test_mtf_ltf_aligned(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BEARISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH),
        }
        self.assertEqual(
            node.get_alignment_for_set("SET_2"),
            FractalAlignment.MTF_LTF_ALIGNED,
        )

    def test_conflicting(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BEARISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH),
            "4h": _make_tf_state("4h", trend=TrendDirection.BEARISH),
        }
        self.assertEqual(
            node.get_alignment_for_set("SET_2"),
            FractalAlignment.CONFLICTING,
        )

    def test_transitional_when_range(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.RANGE),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH),
        }
        self.assertEqual(
            node.get_alignment_for_set("SET_2"),
            FractalAlignment.TRANSITIONAL,
        )


class TestCrossSetCoherenceTracker(unittest.TestCase):
    """Tests for event deduplication across sets."""

    def test_first_registration_is_new(self):
        tracker = CrossSetCoherenceTracker()
        self.assertTrue(tracker.register_event("4h", 100, "CHOCH_BULLISH", "SET_2"))

    def test_duplicate_same_set_rejected(self):
        tracker = CrossSetCoherenceTracker()
        tracker.register_event("4h", 100, "CHOCH_BULLISH", "SET_2")
        self.assertFalse(tracker.register_event("4h", 100, "CHOCH_BULLISH", "SET_2"))

    def test_same_event_different_set_allowed(self):
        tracker = CrossSetCoherenceTracker()
        tracker.register_event("4h", 100, "CHOCH_BULLISH", "SET_2")
        self.assertTrue(tracker.register_event("4h", 100, "CHOCH_BULLISH", "SET_3"))

    def test_cross_set_consumers(self):
        tracker = CrossSetCoherenceTracker()
        tracker.register_event("4h", 100, "BOS_BEARISH", "SET_2")
        tracker.register_event("4h", 100, "BOS_BEARISH", "SET_3")
        consumers = tracker.get_cross_set_consumers("4h", 100, "BOS_BEARISH")
        self.assertEqual(consumers, {"SET_2", "SET_3"})

    def test_reset_clears_all(self):
        tracker = CrossSetCoherenceTracker()
        tracker.register_event("4h", 100, "BOS_BEARISH", "SET_2")
        tracker.reset()
        self.assertTrue(tracker.register_event("4h", 100, "BOS_BEARISH", "SET_2"))


class TestConditionalHypothesisEngine(unittest.TestCase):
    """Tests for the hypothesis evaluation engine."""

    def setUp(self):
        self.engine = ConditionalHypothesisEngine()

    def test_continuation_bullish_hypothesis(self):
        """Bullish HTF + Discount MTF + Bullish LTF CHOCH -> valid continuation hypothesis."""
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.CHOCH_BULLISH,
                                     trigger_price=100.0,
                                     broken_swing_price=95.0,
                                 )]),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.CHOCH_BULLISH,
                                     trigger_price=100.0,
                                     broken_swing_price=95.0,
                                 )]),
        }

        hyp = self.engine.evaluate_hypothesis(node, "SET_2", "CONTINUATION")
        self.assertIsNotNone(hyp)
        self.assertEqual(hyp.expected_direction, 1)
        self.assertEqual(hyp.htf_bias, TrendDirection.BULLISH)
        self.assertGreater(hyp.confidence_score, 0.0)

    def test_pullback_bearish_hypothesis(self):
        """Bullish HTF, pullback type -> expected short direction."""
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BEARISH, pd_zone="PREMIUM",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.BOS_BEARISH,
                                     trigger_price=100.0,
                                     broken_swing_price=105.0,
                                 )]),
            "4h": _make_tf_state("4h", trend=TrendDirection.BEARISH, pd_zone="PREMIUM",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.BOS_BEARISH,
                                     trigger_price=100.0,
                                     broken_swing_price=105.0,
                                 )]),
        }

        hyp = self.engine.evaluate_hypothesis(node, "SET_2", "PULLBACK")
        self.assertIsNotNone(hyp)
        self.assertEqual(hyp.expected_direction, -1)

    def test_no_hypothesis_when_htf_neutral(self):
        """Neutral HTF -> no hypothesis."""
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.NEUTRAL),
            "1d": _make_tf_state("1d"),
            "4h": _make_tf_state("4h"),
        }
        hyp = self.engine.evaluate_hypothesis(node, "SET_2", "CONTINUATION")
        self.assertIsNone(hyp)

    def test_no_hypothesis_without_ltf_break(self):
        """No LTF break -> no hypothesis."""
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT"),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT"),
        }
        hyp = self.engine.evaluate_hypothesis(node, "SET_2", "CONTINUATION")
        self.assertIsNone(hyp)

    def test_cross_set_support_counted(self):
        """Cross-set support should increase when multiple HTFs agree."""
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1M": _make_tf_state("1M", trend=TrendDirection.BULLISH),
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.BOS_BULLISH,
                                     trigger_price=100.0,
                                     broken_swing_price=95.0,
                                 )]),
            "4h": _make_tf_state("4h", trend=TrendDirection.BULLISH, pd_zone="DISCOUNT",
                                 breaks=[StructuralBreak(
                                     timestamp_ms=99,
                                     break_type=StructuralBreakType.BOS_BULLISH,
                                     trigger_price=100.0,
                                     broken_swing_price=95.0,
                                 )]),
            "1h": _make_tf_state("1h", trend=TrendDirection.BULLISH),
        }

        support = self.engine._count_cross_set_support(node, "SET_2", 1)
        self.assertGreater(support, 0)


class TestFractalStateEngine(unittest.TestCase):
    """Integration tests for the full FractalStateEngine."""

    def _make_dummy_data(self, n: int = 200) -> Dict:
        """Create dummy OHLCV data."""
        ts = np.arange(n, dtype=np.int64) * 3600000 + 1600000000000
        close_ts = ts + 3599999
        c = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
        o = c - np.random.rand(n) * 0.3
        h = np.maximum(o, c) + np.random.rand(n) * 0.5
        l = np.minimum(o, c) - np.random.rand(n) * 0.5
        v = np.random.rand(n) * 1000.0

        return {"ts": ts, "close_ts": close_ts, "o": o, "h": h, "l": l, "c": c, "v": v}

    def test_engine_initialization(self):
        engine = FractalStateEngine(symbol="BTCUSDT")
        self.assertEqual(engine.symbol, "BTCUSDT")
        self.assertEqual(len(engine._generators), 7)

    def test_load_data(self):
        engine = FractalStateEngine(symbol="BTCUSDT")
        data = {"1d": self._make_dummy_data(), "4h": self._make_dummy_data()}
        engine.load_data(data)
        self.assertEqual(len(engine._data), 2)

    def test_get_fractal_summary(self):
        node = FractalStateNode(timestamp_ms=100)
        node.states = {
            "1w": _make_tf_state("1w", trend=TrendDirection.BULLISH),
            "1d": _make_tf_state("1d", trend=TrendDirection.BEARISH),
        }
        node.fractal_bias = FractalBias.WEAK_BULLISH
        node.alignment = FractalAlignment.CONFLICTING
        node.active_sets = ["SET_2"]

        engine = FractalStateEngine(symbol="BTCUSDT")
        summary = engine.get_fractal_summary(node)

        self.assertEqual(summary["timestamp_ms"], 100)
        self.assertEqual(summary["fractal_bias"], "WEAK_BULLISH")
        self.assertIn("1w", summary["timeframe_states"])
        self.assertIn("SET_2", summary["set_alignments"])


# Need Dict import for type annotations used in tests
from typing import Dict


if __name__ == "__main__":
    unittest.main()
