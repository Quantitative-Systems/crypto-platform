"""
Unit Tests for Product 04: Causal Replayer
"""

import pytest
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer


def generate_candle_series(count: int, start_ts: int = 1000, step_ms: int = 60000, base_price: float = 100.0):
    candles = []
    p = base_price
    for i in range(count):
        # Create zigzag price action
        delta = 2.0 if i % 2 == 0 else -1.0
        p += delta
        candles.append(Candle(
            timestamp=start_ts + (i * step_ms),
            open=p - delta,
            high=p + 3.0,
            low=p - 3.0,
            close=p,
            volume=50.0 + i
        ))
    return candles


def test_replayer_runs_without_exceptions_on_synthetic_data():
    replayer = CausalReplayer(timeframe_set_id="SET_4", initial_balance=10000.0)

    # 4H, 1H, 15M synthetic streams
    htf_candles = generate_candle_series(20, start_ts=0, step_ms=4 * 3600 * 1000, base_price=50000.0)
    mtf_candles = generate_candle_series(40, start_ts=0, step_ms=3600 * 1000, base_price=50000.0)
    ltf_candles = generate_candle_series(100, start_ts=0, step_ms=15 * 60 * 1000, base_price=50000.0)

    result = replayer.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles,
        min_lookback_bars=10
    )

    assert "metrics" in result
    assert "exit_attribution" in result
    assert "failure_modes" in result
    assert "closed_trades" in result
    assert "equity_curve" in result
    assert len(result["equity_curve"]) >= 1


def test_terminal_candidate_never_reenters_regression_invariant():
    """
    REGRESSION INVARIANT (Day 40 Infrastructure Audit):
    A terminal candidate / trade MUST NEVER re-enter: candidate -> risk -> execution.
    1 unique candidate ID -> at most 1 genuine execution.
    """
    from strategy_engine.contracts.trade_plan import TradePlanPayload
    from strategy_engine.contracts.strategy_state import CandidateState, PositionState
    from strategy_engine.contracts.trade_plan import DirectionalPermission

    replayer = CausalReplayer(timeframe_set_id="SET_4", initial_balance=10000.0)

    cand_id = "cand_REGRESSION_TEST_001"
    
    # 1. Simulate entry proposal
    plan_entry = TradePlanPayload(
        trade_plan_id=cand_id,
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        directional_permission=DirectionalPermission.PERMIT_LONG.value,
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=95.0,
        target_price=125.0,
        raw_rr=5.0,
        status=CandidateState.ENTERED.value,
        position_status=PositionState.ACTIVE_POSITION.value
    )
    
    # Evaluate proposal in mock coordinator
    replayer.strategy_coordinator.evaluate = lambda h, m, l: [plan_entry]

    htf_candles = generate_candle_series(20, start_ts=0, step_ms=4 * 3600 * 1000, base_price=100.0)
    mtf_candles = generate_candle_series(40, start_ts=0, step_ms=3600 * 1000, base_price=100.0)
    ltf_candles = generate_candle_series(100, start_ts=0, step_ms=15 * 60 * 1000, base_price=100.0)

    # First bar sets it as pending, next bar fills it
    # Now simulate active manager emitting an EXIT plan with status=ENTERED and position_status=MTF_TRAIL_EXIT
    plan_exit = TradePlanPayload(
        trade_plan_id=cand_id,
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        directional_permission=DirectionalPermission.PERMIT_LONG.value,
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=102.0,
        target_price=125.0,
        raw_rr=5.0,
        status=CandidateState.ENTERED.value,
        position_status=PositionState.MTF_TRAIL_EXIT.value
    )

    call_count = [0]
    def dynamic_evaluate(h, m, l):
        call_count[0] += 1
        if call_count[0] == 1:
            return [plan_entry]
        elif call_count[0] == 2:
            return [plan_exit]
        return []

    replayer.strategy_coordinator.evaluate = dynamic_evaluate

    result = replayer.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles,
        min_lookback_bars=10
    )

    closed = result["closed_trades"]
    executed_ids = [t["trade_id"] for t in closed if t["trade_id"] == cand_id]
    # Invariant: Must execute at most 1 time, never duplicate
    assert len(executed_ids) <= 1, f"Expected at most 1 execution for {cand_id}, got {len(executed_ids)}"

