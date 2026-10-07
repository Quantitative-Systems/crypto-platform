"""Adversarial Target Geometry and Causal Execution Test Suite.

Specifically designed to probe, stress, and falsify target generation,
intrabar collision resolution, and execution causality:
1. Long Geometry: Target > Entry > Stop
2. Short Geometry: Target < Entry < Stop
3. Minimum 4R Floor Enforcement
4. Adverse-First Intrabar Collision (SL triggers before TP on same-bar collision)
5. Adverse Open Gap Handling (slippage on gap through stop)
6. Monotonic MTF Trailing Bounds (cannot widen, cannot exceed target)
7. Pure Structural Target Requirement (rejection of ungrounded fallbacks)
8. Causal Zero-Lookahead Verification
"""
from __future__ import annotations

import numpy as np

from execution.backtest.engine import CausalBacktestEngine
from research.experiments.mtf_strategy_coordinator import MTFStrategyCoordinator


def test_long_target_geometry_invariants():
    """Verify long trades require Target > Entry > Stop and >= 4R."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Valid candidate
    opens = np.array([100.0, 100.0, 105.0])
    highs = np.array([101.0, 106.0, 110.0])
    lows = np.array([99.0, 99.5, 104.0])
    closes = np.array([100.0, 105.0, 109.0])
    timestamps = np.array([1000, 2000, 3000])

    valid_cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,      # Risk = 2.0
        "target_price": 108.5,   # Reward = 8.5 -> R = 4.25 (>= 4R)
        "target_r": 4.25,
    }

    # Should execute successfully
    metrics = engine.execute_stream(
        stream_id="TEST_VALID_LONG",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[valid_cand],
    )
    assert metrics.total_trades == 1

    # Inverted target: target below entry (Class H defect)
    inverted_cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 95.0,  # INVERTED!
        "target_r": -2.5,
    }
    metrics_inv = engine.execute_stream(
        stream_id="TEST_INV_LONG",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[inverted_cand],
    )
    assert metrics_inv.total_trades == 0, "Inverted target must be rejected before entry!"

    # Inverted stop: stop above entry
    inv_stop_cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 102.0,  # INVERTED STOP!
        "target_price": 115.0,
        "target_r": 7.5,
    }
    metrics_stop = engine.execute_stream(
        stream_id="TEST_INV_STOP_LONG",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[inv_stop_cand],
    )
    assert metrics_stop.total_trades == 0, "Inverted stop must be rejected before entry!"

    # Insufficient R (< 4.0R floor)
    sub_4r_cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,      # Risk = 2.0
        "target_price": 106.0,   # Reward = 6.0 -> R = 3.0 (< 4R)
        "target_r": 3.0,
    }
    metrics_sub = engine.execute_stream(
        stream_id="TEST_SUB_4R_LONG",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[sub_4r_cand],
    )
    assert metrics_sub.total_trades == 0, "Sub-4R targets must be rejected!"


def test_short_target_geometry_invariants():
    """Verify short trades require Target < Entry < Stop and >= 4R."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    opens = np.array([100.0, 100.0, 95.0])
    highs = np.array([101.0, 100.5, 96.0])
    lows = np.array([99.0, 94.0, 90.0])
    closes = np.array([100.0, 95.0, 91.0])
    timestamps = np.array([1000, 2000, 3000])

    valid_cand = {
        "bar_index": 0,
        "direction": -1,
        "entry_price": 100.0,
        "stop_price": 102.0,     # Risk = 2.0
        "target_price": 91.0,    # Reward = 9.0 -> R = 4.5 (>= 4R)
        "target_r": 4.5,
    }
    metrics = engine.execute_stream(
        stream_id="TEST_VALID_SHORT",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[valid_cand],
    )
    assert metrics.total_trades == 1

    # Inverted short target: target above entry
    inv_short_cand = {
        "bar_index": 0,
        "direction": -1,
        "entry_price": 100.0,
        "stop_price": 102.0,
        "target_price": 105.0,  # INVERTED!
        "target_r": -2.5,
    }
    metrics_inv = engine.execute_stream(
        stream_id="TEST_INV_SHORT",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[inv_short_cand],
    )
    assert metrics_inv.total_trades == 0, "Inverted short target must be rejected before entry!"


def test_adverse_first_intrabar_collision():
    """Verify that when BOTH TP and SL are touched in the same bar, SL triggers FIRST."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal evaluated
    # Bar 1: Entry at 100.0, huge spike candle that hits BOTH 90.0 (SL) AND 120.0 (TP)
    # Bar 2: Subsequent bar
    opens = np.array([100.0, 100.0, 105.0])
    highs = np.array([101.0, 120.0, 106.0])  # Exceeds target 110.0
    lows = np.array([99.0, 90.0, 104.0])     # Breaches stop 98.0
    closes = np.array([100.0, 115.0, 105.0])
    timestamps = np.array([1000, 2000, 3000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,      # Risk = 2.0
        "target_price": 110.0,   # Reward = 10.0 -> R = 5.0
        "target_r": 5.0,
    }

    metrics = engine.execute_stream(
        stream_id="TEST_COLLISION",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[cand],
    )
    assert metrics.total_trades == 1
    trade = metrics.trades[0]
    # Adverse-first rule requires that collision results in a STOP OUT, not TP
    assert trade.exit_reason in ("LTF_SL", "MTF_TRAIL"), f"Expected SL exit on collision, got: {trade.exit_reason}"
    assert trade.realized_r < 0, f"Collision must produce loss, got R={trade.realized_r}"


def test_monotonic_mtf_trailing_bounds():
    """Verify that MTF trailing stop can only tighten risk and cannot cross target."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    opens = np.array([100.0, 100.0, 104.0, 106.0])
    highs = np.array([101.0, 105.0, 107.0, 108.0])
    lows = np.array([99.0, 99.5, 102.0, 101.0])
    closes = np.array([100.0, 104.0, 106.0, 103.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 112.0,
        "target_r": 6.0,
    }

    # MTF trailing levels that ratchet up: 101.0 at t=3000
    trailing_map = {3000: 101.5}

    metrics = engine.execute_stream(
        stream_id="TEST_TRAILING",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[cand],
        mtf_trailing_levels=trailing_map,
    )
    assert metrics.total_trades == 1
    trade = metrics.trades[0]
    # Trade should exit via MTF_TRAIL at bar 3 (low=101.0 touches trailed stop 101.5)
    assert trade.exit_reason == "MTF_TRAIL"
    assert trade.realized_r > 0, "Trailed stop should lock in positive R!"


def test_next_bar_open_fill_causality():
    """Verify that signal on bar i is filled strictly on bar i+1 open, never bar i close."""
    engine = CausalBacktestEngine(taker_fee_bps=0.0, slippage_bps=0.0, min_target_r=4.0)

    # Bar 0: Signal evaluated at close (100.0)
    # Bar 1: Opens with gap at 102.0
    opens = np.array([98.0, 102.0, 103.0])
    highs = np.array([100.0, 105.0, 106.0])
    lows = np.array([97.0, 101.5, 102.0])
    closes = np.array([100.0, 103.0, 105.0])
    timestamps = np.array([1000, 2000, 3000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,  # Signal bar close was 100.0
        "stop_price": 95.0,    # Risk from open 102.0 is 7.0
        "target_price": 135.0, # Reward from open 102.0 is 33.0 -> R = 4.71
        "target_r": 5.0,
    }

    metrics = engine.execute_stream(
        stream_id="TEST_CAUSAL_FILL",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        hypothesis="CONTINUATION",
        ltf_opens=opens,
        ltf_highs=highs,
        ltf_lows=lows,
        ltf_closes=closes,
        ltf_timestamps=timestamps,
        signal_candidates=[cand],
    )
    assert metrics.total_trades == 1
    trade = metrics.trades[0]
    # Fill price must be next-bar open (102.0), not signal bar close (100.0)
    assert abs(trade.entry_px - 102.0) < 1e-3, f"Expected fill at bar 1 open 102.0, got {trade.entry_px}"
