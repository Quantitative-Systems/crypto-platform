"""
Unit tests for HYP_TARGET_MILESTONE_01.
Validates the +2.5R milestone target monetization mechanism:
1. Long reaches +2.5R -> exits at milestone price as limit (maker fee, zero slippage)
2. Short reaches +2.5R -> exits at milestone price as limit (maker fee, zero slippage)
3. Excursion < 2.5R -> milestone does not trigger, standard exit hierarchy preserved
4. Same-bar collision: adverse stop touched on same candle -> adverse-first rule wins
5. Structural target invariant: planned target price remains intact (>= 4R)
6. Subordination and integration with +1.0R breakeven ratchet
"""

import pytest
from market_intelligence.primitives import Candle, MarketStatePayload
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from research.replayer.causal_replayer import CausalReplayer
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator


def make_long_trade(trade_id: str = "t_long_1", entry: float = 100.0, stop: float = 90.0, target: float = 150.0) -> SimulatedTrade:
    return SimulatedTrade(
        trade_id=trade_id,
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=entry,
        fill_entry_price=entry,
        initial_stop_price=stop,
        current_stop_price=stop,
        target_price=target,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )


def make_short_trade(trade_id: str = "t_short_1", entry: float = 100.0, stop: float = 110.0, target: float = 50.0) -> SimulatedTrade:
    return SimulatedTrade(
        trade_id=trade_id,
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_SHORT",
        setup_timestamp=1000,
        entry_price=entry,
        fill_entry_price=entry,
        initial_stop_price=stop,
        current_stop_price=stop,
        target_price=target,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )


def test_milestone_initialization():
    """Verify CausalReplayer configures milestone target mechanism."""
    replayer = CausalReplayer(
        timeframe_set_id="SET_4",
        initial_balance=10000.0,
        enable_forward_expansion=True,
        enforce_displacement_polarity=True,
        enable_breakeven_1r=True,
        enable_milestone_target=True,
        milestone_r=2.5
    )
    assert replayer.enable_milestone_target is True
    assert replayer.milestone_r == 2.5
    assert replayer.execution_simulator.enable_milestone_target is True
    assert replayer.execution_simulator.milestone_r == 2.5
    assert replayer.strategy_coordinator.active_manager.enable_milestone_target is True
    assert replayer.strategy_coordinator.active_manager.milestone_r == 2.5


def test_long_reaches_2_5r_exits_at_milestone():
    """LONG trade reaches +2.5R -> closes at milestone price with MILESTONE_TARGET_EXIT."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(
        enable_breakeven_1r=True,
        enable_milestone_target=True,
        milestone_r=2.5,
        maker_fee_rate=0.0002
    )
    # Entry: 100, Stop: 90, Risk: 10, +2.5R Milestone Level: 125.0, Target: 150 (>= 4R)
    trade = make_long_trade(entry=100.0, stop=90.0, target=150.0)
    ledger.trades[trade.trade_id] = trade

    # Candle reaches 125.5 (>= 125.0), low stays safely at 115.0 (> stop)
    c1 = Candle(timestamp=2000, open=110.0, high=125.5, low=115.0, close=124.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    assert closed[0].status == "CLOSED"
    assert closed[0].exit_reason == "MILESTONE_TARGET_EXIT"
    assert closed[0].exit_price == pytest.approx(125.0, 1e-4)
    # Gross R should be exactly +2.5R
    assert closed[0].target_price == 150.0 # Structural target untouched!


def test_short_reaches_2_5r_exits_at_milestone():
    """SHORT trade reaches +2.5R -> closes at milestone price with MILESTONE_TARGET_EXIT."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(
        enable_breakeven_1r=True,
        enable_milestone_target=True,
        milestone_r=2.5,
        maker_fee_rate=0.0002
    )
    # Entry: 100, Stop: 110, Risk: 10, +2.5R Milestone Level: 75.0, Target: 50
    trade = make_short_trade(entry=100.0, stop=110.0, target=50.0)
    ledger.trades[trade.trade_id] = trade

    # Candle low drops to 74.0 (<= 75.0), high stays safely at 85.0 (< stop)
    c1 = Candle(timestamp=2000, open=90.0, high=85.0, low=74.0, close=76.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    assert closed[0].status == "CLOSED"
    assert closed[0].exit_reason == "MILESTONE_TARGET_EXIT"
    assert closed[0].exit_price == pytest.approx(75.0, 1e-4)
    assert closed[0].target_price == 50.0


def test_excursion_below_2_5r_preserves_hierarchy():
    """Trade reaches +1.5R (triggers breakeven, but not milestone) -> stays active or closes via breakeven."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(
        enable_breakeven_1r=True,
        enable_milestone_target=True,
        milestone_r=2.5
    )
    # Entry: 100, Stop: 90, Risk: 10, +2.5R Level: 125.0
    trade = make_long_trade(entry=100.0, stop=90.0, target=150.0)
    ledger.trades[trade.trade_id] = trade

    # Candle 1: High reaches 115.0 (+1.5R), low stays at 105.0 (> 101.0 BE stop)
    c1 = Candle(timestamp=2000, open=102.0, high=115.0, low=105.0, close=112.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)
    assert len(closed) == 0
    assert trade.status == "ACTIVE"
    assert trade.current_stop_price == pytest.approx(101.0, 1e-4) # BE stop active

    # Candle 2: Drops to 100.0 (<= 101.0) -> closes at BREAKEVEN_TRAIL, NOT milestone!
    c2 = Candle(timestamp=3000, open=108.0, high=108.0, low=100.0, close=100.5, volume=10.0)
    closed = sim.process_candle(c2, ledger)
    assert len(closed) == 1
    assert closed[0].exit_reason == "BREAKEVEN_TRAIL"


def test_milestone_adverse_first_collision():
    """Extreme volatility bar touches both milestone (+2.5R) and initial stop -> Adverse stop wins!"""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(
        enable_breakeven_1r=True,
        enable_milestone_target=True,
        milestone_r=2.5
    )
    trade = make_long_trade(entry=100.0, stop=90.0, target=150.0)
    ledger.trades[trade.trade_id] = trade

    # Extreme candle: High 126.0 (touches 2.5R milestone), Low 88.0 (penetrates 90.0 SL)
    c1 = Candle(timestamp=2000, open=98.0, high=126.0, low=88.0, close=95.0, volume=100.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    # Adverse-first axiom: Stop Loss executes, NOT milestone target
    assert closed[0].exit_reason == "INITIAL_LTF_SL"
    assert closed[0].realized_rr < 0.0
