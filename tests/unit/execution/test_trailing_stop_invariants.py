"""Deterministic tests for trailing-stop validity, bar-0 invariants, and fill price bounds.

Verifies:
1. Long positions with invalid trailing stops (above open / bar-0 / exceeding target).
2. Short positions with invalid trailing stops (below open / bar-0 / exceeding target).
3. Valid long and short trailing stops tightening monotonically on subsequent bars.
4. Stop updates across subsequent candles.
5. Same-bar entry and exit behavior.
6. Fill-price bounds (strictly within [candle.low, candle.high] and gap handling).
7. Regression test for the MTF trailing stop inversion defect.
"""
from __future__ import annotations

import numpy as np
import pytest

from execution.backtest.engine import CausalBacktestEngine


def test_long_invalid_trailing_stop_rejected():
    """Verify that an invalid trailing stop (above open or on entry bar) cannot trigger an artificial exit."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # 4 flat candles around 100.0
    opens = np.array([100.0, 100.0, 100.0, 100.0])
    highs = np.array([101.0, 101.0, 101.0, 101.0])
    lows = np.array([99.0, 99.0, 99.0, 99.0])
    closes = np.array([100.0, 100.0, 100.0, 100.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 110.0,
        "target_r": 5.0,
    }

    # Defect condition: MTF trailing level provided at entry bar (t=2000) at 105.0 (above entry and candle high!)
    trailing_map = {2000: 105.0}

    metrics = engine.execute_stream(
        stream_id="TEST_LONG_INV",
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
    # Trade must NOT exit via MTF_TRAIL on entry bar
    assert trade.exit_reason != "MTF_TRAIL", "Invalid stop on entry bar must never trigger MTF_TRAIL!"
    assert trade.bars_held > 0, "Must not be closed on entry bar by invalid trailing stop!"
    assert trade.exit_reason == "TIME_EXIT"


def test_short_invalid_trailing_stop_rejected():
    """Verify that an invalid short trailing stop (below open or on entry bar) cannot trigger an artificial exit."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    opens = np.array([100.0, 100.0, 100.0, 100.0])
    highs = np.array([101.0, 101.0, 101.0, 101.0])
    lows = np.array([99.0, 99.0, 99.0, 99.0])
    closes = np.array([100.0, 100.0, 100.0, 100.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": -1,
        "entry_price": 100.0,
        "stop_price": 102.0,
        "target_price": 90.0,
        "target_r": 5.0,
    }

    # Defect condition: MTF trailing level provided at entry bar (t=2000) at 95.0 (below entry and candle low!)
    trailing_map = {2000: 95.0}

    metrics = engine.execute_stream(
        stream_id="TEST_SHORT_INV",
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
    assert trade.exit_reason != "MTF_TRAIL"
    assert trade.bars_held > 0
    assert trade.exit_reason == "TIME_EXIT"


def test_valid_long_trailing_stop_ratchet():
    """Verify that a valid long trailing stop properly locks in profit on subsequent bars."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal evaluated at 100.0
    # Bar 1: Entry at 100.0, rallies to 105.0
    # Bar 2: Opens at 104.0, rallies to 107.0, low 102.0. Trailing level at 101.5 (< op=104.0, > sl=98.0)
    # Bar 3: Opens at 106.0, pulls back to 101.0 (triggers trailing stop at 101.5)
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

    trailing_map = {3000: 101.5}

    metrics = engine.execute_stream(
        stream_id="TEST_VALID_LONG_TRAIL",
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
    assert trade.exit_reason == "MTF_TRAIL"
    assert trade.bars_held == 2
    assert trade.realized_r > 0
    # Exit price must be within bar 3 range [101.0, 108.0]
    assert 101.0 <= trade.exit_px <= 108.0


def test_valid_short_trailing_stop_ratchet():
    """Verify that a valid short trailing stop properly locks in profit on subsequent bars."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal at 100.0
    # Bar 1: Entry at 100.0, drops to 95.0
    # Bar 2: Opens at 96.0, drops to 93.0, high 97.0. Trailing level at 98.5 (> op=96.0, < sl=102.0)
    # Bar 3: Opens at 94.0, bounces to 99.0 (triggers trailing stop at 98.5)
    opens = np.array([100.0, 100.0, 96.0, 94.0])
    highs = np.array([101.0, 100.5, 97.0, 99.0])
    lows = np.array([99.0, 95.0, 93.0, 92.0])
    closes = np.array([100.0, 96.0, 94.0, 97.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": -1,
        "entry_price": 100.0,
        "stop_price": 102.0,
        "target_price": 88.0,
        "target_r": 6.0,
    }

    trailing_map = {3000: 98.5}

    metrics = engine.execute_stream(
        stream_id="TEST_VALID_SHORT_TRAIL",
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
    assert trade.exit_reason == "MTF_TRAIL"
    assert trade.bars_held == 2
    assert trade.realized_r > 0
    # Exit price must be within bar 3 range [92.0, 99.0]
    assert 92.0 <= trade.exit_px <= 99.0


def test_subsequent_candle_stop_updates():
    """Verify multiple trailing stop updates across progressive candles."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Progressive trend up
    opens = np.array([100.0, 100.0, 105.0, 110.0, 112.0])
    highs = np.array([101.0, 106.0, 111.0, 114.0, 113.0])
    lows = np.array([99.0, 99.5, 104.0, 108.0, 106.0])
    closes = np.array([100.0, 105.0, 110.0, 112.0, 107.0])
    timestamps = np.array([1000, 2000, 3000, 4000, 5000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 120.0,
        "target_r": 10.0,
    }

    # Progressive stop ratchets: 102.0 at bar 2, 107.5 at bar 3
    trailing_map = {
        3000: 102.0,  # Valid on bar 2 (op=105.0 > 102.0)
        4000: 107.5,  # Valid on bar 3 (op=110.0 > 107.5)
    }

    metrics = engine.execute_stream(
        stream_id="TEST_MULTI_STEP_TRAIL",
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

    trade = metrics.trades[0]
    # Stopped out at bar 4 where low=106.0 touches trailed stop 107.5
    assert trade.exit_reason == "MTF_TRAIL"
    assert trade.bars_held == 3
    assert abs(trade.exit_px - 107.5) < 0.2  # Filled at 107.5 minus slippage
    assert trade.realized_r > 3.0, "Should have locked in > 3R of profit!"


def test_same_bar_entry_and_exit_deterministic():
    """Verify deterministic same-bar exit when initial stop loss is hit on the entry bar."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 1: Entry at 100.0, low crashes to 95.0 (breaches initial_sl=98.0)
    opens = np.array([100.0, 100.0, 96.0])
    highs = np.array([101.0, 101.0, 97.0])
    lows = np.array([99.0, 95.0, 94.0])
    closes = np.array([100.0, 96.0, 95.0])
    timestamps = np.array([1000, 2000, 3000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 110.0,
        "target_r": 5.0,
    }

    metrics = engine.execute_stream(
        stream_id="TEST_SAME_BAR_SL",
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

    trade = metrics.trades[0]
    assert trade.bars_held == 0
    assert trade.exit_reason == "LTF_SL"
    assert trade.realized_r < 0
    assert abs(trade.exit_px - 98.0) < 0.1


def test_adverse_gap_fill_bounds():
    """Verify that an adverse opening gap past stop loss executes at the open price, not above it."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 1: Entry at 100.0, rallies to 105.0. Stop at 98.0.
    # Bar 2: Flash crash gap open at 94.0 (below stop 98.0!). High is only 95.0!
    opens = np.array([100.0, 100.0, 94.0])
    highs = np.array([101.0, 105.0, 95.0])
    lows = np.array([99.0, 99.5, 92.0])
    closes = np.array([100.0, 104.0, 93.0])
    timestamps = np.array([1000, 2000, 3000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 110.0,
        "target_r": 5.0,
    }

    metrics = engine.execute_stream(
        stream_id="TEST_GAP_SL",
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

    trade = metrics.trades[0]
    assert trade.exit_reason == "LTF_SL"
    # Execution must fill at open (94.0), NEVER at stop (98.0) which was outside candle range [92.0, 95.0]
    assert trade.exit_px <= 95.0, f"Exit price {trade.exit_px} exceeded candle high 95.0!"
    assert trade.exit_px >= 92.0, f"Exit price {trade.exit_px} fell below candle low 92.0!"
    assert abs(trade.exit_px - 94.0) < 0.1


def test_regression_lin_00046_defect():
    """Direct regression test replicating the LIN_00046 inverted stop condition."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Replicate LIN_00046 candle: Open 502.70, High 521.70, Low 497.10, Close 519.80
    opens = np.array([500.0, 502.70, 520.0])
    highs = np.array([505.0, 521.70, 525.0])
    lows = np.array([495.0, 497.10, 515.0])
    closes = np.array([502.70, 519.80, 522.0])
    timestamps = np.array([1636240000000, 1636243200000, 1636246400000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 502.70,
        "stop_price": 473.74,
        "target_price": 630.00,
        "target_r": 4.4,
    }

    # Defect: MTF major low at 552.99 provided at entry bar (1636243200000)
    trailing_map = {1636243200000: 552.99}

    metrics = engine.execute_stream(
        stream_id="TEST_REGRESSION_LIN_00046",
        symbol="BNBUSDT",
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

    trade = metrics.trades[0]
    # In the original buggy engine, this filled at 552.99 on bar 0 (phantom win)!
    # With the fix:
    assert trade.exit_reason != "MTF_TRAIL", "Defect re-occurred: MTF_TRAIL triggered at entry bar!"
    assert trade.bars_held > 0, "Trade must not exit on bar 0 due to inverted stop!"
    assert trade.exit_px <= 525.0, "Exit price must never exceed candle high!"


def test_adverse_gap_through_ratcheted_trailing_stop():
    """Verify an adverse opening gap past an already-ratcheted trailing stop fills at open."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal evaluated at 100.0
    # Bar 1: Entry at 100.0, rallies to 108.0
    # Bar 2: Opens at 105.0, rallies to 108.0, low 104.0. Trailing level ratchets to 102.0 (< op=105.0)
    # Bar 3: Flash crash gap open at 99.0 (below trailed stop 102.0!). High is only 100.0.
    opens = np.array([100.0, 100.0, 105.0, 99.0])
    highs = np.array([101.0, 108.0, 108.0, 100.0])
    lows = np.array([99.0, 99.5, 104.0, 97.0])
    closes = np.array([100.0, 106.0, 107.0, 98.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 95.0,
        "target_price": 120.0,
        "target_r": 4.0,
    }

    trailing_map = {3000: 102.0}

    metrics = engine.execute_stream(
        stream_id="TEST_GAP_TRAILED_SL",
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

    trade = metrics.trades[0]
    assert trade.exit_reason == "MTF_TRAIL", f"Expected MTF_TRAIL exit, got: {trade.exit_reason}"
    assert trade.bars_held == 2, f"Expected 2 bars held, got: {trade.bars_held}"
    # Must fill at open (99.0), NEVER at trailed stop price (102.0) which was above candle high (100.0)
    assert trade.exit_px <= 100.0, f"Exit price {trade.exit_px} exceeded candle high 100.0!"
    assert trade.exit_px >= 97.0, f"Exit price {trade.exit_px} fell below candle low 97.0!"
    assert abs(trade.exit_px - 99.0) < 0.1, f"Expected fill at open 99.0, got: {trade.exit_px}"


def test_ratcheted_trailing_stop_and_target_collision_adverse_first():
    """Verify that when a candle touches both an already-ratcheted trailing stop and target, ADVERSE_FIRST triggers stop."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal evaluated at 100.0
    # Bar 1: Entry at 100.0, rallies to 108.0
    # Bar 2: Opens at 105.0, low 104.0, high 108.0. Trailing level ratchets to 103.0 (< op=105.0)
    # Bar 3: Extreme volatility candle touches BOTH 103.0 (trailed SL) AND 110.0 (TP):
    #        op=106.0, hi=115.0 (exceeds TP), lo=101.0 (breaches trailed SL), cl=110.0
    opens = np.array([100.0, 100.0, 105.0, 106.0])
    highs = np.array([101.0, 108.0, 108.0, 115.0])
    lows = np.array([99.0, 99.5, 104.0, 101.0])
    closes = np.array([100.0, 106.0, 107.0, 110.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 110.0,
        "target_r": 5.0,
    }

    trailing_map = {3000: 103.0}

    metrics = engine.execute_stream(
        stream_id="TEST_COLLISION_TRAILED_SL",
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

    trade = metrics.trades[0]
    # Under ADVERSE_FIRST policy, SL check precedes TP check
    assert trade.exit_reason == "MTF_TRAIL", f"ADVERSE_FIRST requires MTF_TRAIL on collision, got: {trade.exit_reason}"
    assert trade.bars_held == 2
    # Exit price should be 103.0 (minus slippage), NOT target 110.0
    assert abs(trade.exit_px - 103.0) < 0.2
    # Profit multiple should reflect 103.0 (+1.5R), NOT 110.0 (+5.0R)
    assert trade.realized_r < 2.0, f"Collision must not award target profit, got R={trade.realized_r}"


def test_favorable_target_opening_gap_fill():
    """Verify that a favorable opening gap through profit target executes at the open price."""
    engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # Bar 0: Signal evaluated at 100.0
    # Bar 1: Entry at 100.0, rallies to 106.0
    # Bar 2: Opens at 102.0, rallies to 106.0, low 101.0, close 105.0
    # Bar 3: Huge favorable opening gap at 114.0 (target is 110.0!)
    opens = np.array([100.0, 100.0, 102.0, 114.0])
    highs = np.array([101.0, 106.0, 106.0, 116.0])
    lows = np.array([99.0, 99.5, 101.0, 113.0])
    closes = np.array([100.0, 105.0, 105.0, 115.0])
    timestamps = np.array([1000, 2000, 3000, 4000])

    cand = {
        "bar_index": 0,
        "direction": 1,
        "entry_price": 100.0,
        "stop_price": 98.0,
        "target_price": 110.0,
        "target_r": 5.0,
    }

    metrics = engine.execute_stream(
        stream_id="TEST_FAVORABLE_GAP_TP",
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

    trade = metrics.trades[0]
    assert trade.exit_reason == "HTF_TP", f"Expected HTF_TP, got: {trade.exit_reason}"
    assert trade.bars_held == 2
    # Favorable gap fill must execute at open (114.0), capturing the gap beyond 110.0 target
    assert abs(trade.exit_px - 114.0) < 0.1, f"Expected fill at open 114.0, got: {trade.exit_px}"
    assert 113.0 <= trade.exit_px <= 116.0, f"Exit price {trade.exit_px} outside candle range [113, 116]!"
    assert trade.realized_r > 5.0, f"Should capture favorable gap return, got R={trade.realized_r}"
