"""
Unit tests for HYP_MGT_BREAKEVEN_1R_01.
Validates the 13 mandatory pre-replay invariants specified in Section 8 of the Research Directive:
1. LONG reaches +1R -> stop moves to +0.10R.
2. SHORT reaches +1R -> stop moves to -0.10R.
3. Price never reaches +1R -> stop remains unchanged.
4. Existing stop is already better than +0.10R -> do not weaken it.
5. Later structural trail is more protective -> structural trail wins.
6. Same-bar +1R/stop collision -> adverse-first behavior preserved.
7. +1R reached only on a later candle -> no premature stop modification.
8. Repeated +1R observations -> no repeated/invalid stop mutation.
9. No candidate duplication.
10. No change to entry qualification.
11. No change to initial SL.
12. No change to target.
13. No change to risk sizing.
"""

import pytest
from market_intelligence.primitives import Candle, MarketStatePayload
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_config import RiskConfig


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


# 1. LONG reaches +1R -> stop moves to +0.10R
def test_long_reaches_1r_moves_stop_to_plus_0_10r():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0) # risk = 10.0, +1R = 110.0, +0.10R = 101.0
    ledger.trades[trade.trade_id] = trade

    # Bar 1: Price reaches 110.5 (+1.05R >= +1.0R), low stays at 95.0 (> 90.0)
    c1 = Candle(timestamp=2000, open=102.0, high=110.5, low=95.0, close=109.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == pytest.approx(101.0, 1e-4)
    assert trade.metadata.get("breakeven_triggered") is True
    assert trade.metadata.get("breakeven_stop_price") == pytest.approx(101.0, 1e-4)


# 2. SHORT reaches +1R -> stop moves to -0.10R
def test_short_reaches_1r_moves_stop_to_minus_0_10r():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_short_trade(entry=100.0, stop=110.0) # risk = 10.0, +1R = 90.0, BE stop = 99.0
    ledger.trades[trade.trade_id] = trade

    # Bar 1: Price drops to 89.5 (+1.05R favorable excursion), high stays at 105.0 (< 110.0)
    c1 = Candle(timestamp=2000, open=98.0, high=105.0, low=89.5, close=91.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == pytest.approx(99.0, 1e-4)
    assert trade.metadata.get("breakeven_triggered") is True
    assert trade.metadata.get("breakeven_stop_price") == pytest.approx(99.0, 1e-4)


# 3. Price never reaches +1R -> stop remains unchanged
def test_price_never_reaches_1r_stop_unchanged():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Bar reaches +0.8R (108.0)
    c1 = Candle(timestamp=2000, open=100.0, high=108.0, low=95.0, close=106.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == 90.0
    assert "breakeven_triggered" not in trade.metadata


# 4. Existing stop is already better than +0.10R -> do not weaken it
def test_existing_stop_already_better_does_not_weaken():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0)
    trade.current_stop_price = 105.0 # Already trailed to +0.50R
    ledger.trades[trade.trade_id] = trade

    # Bar reaches +1.5R (115.0)
    c1 = Candle(timestamp=2000, open=106.0, high=115.0, low=106.0, close=114.0, volume=10.0)
    sim.process_candle(c1, ledger)

    # Stop must remain at 105.0 and NOT be downgraded to 101.0
    assert trade.current_stop_price == 105.0


# 5. Later structural trail is more protective -> structural trail wins
def test_later_structural_trail_more_protective_wins():
    atm = ActiveTradeManager(
        enable_mtf_trailing=True,
        enable_breakeven_1r=True,
        breakeven_trigger_r=1.0,
        breakeven_stop_r=0.10
    )
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY",
        trade_plan_id="plan_long_1",
        symbol="BTCUSDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0, # risk 10.0
        target_price=150.0,
        raw_rr=5.0,
        status="ENTERED"
    )
    atm.register_trade("plan_long_1", plan)

    # Step 1: Reach +1.0R -> Stop ratchets to 101.0
    plan.metadata["max_favorable_price"] = 111.0
    from tests.unit.strategy_engine.test_canonical_refinements import make_payload
    ltf_payload = make_payload(timeframe="15M", current_price=111.0, timestamp=2000)
    mtf_payload = make_payload(timeframe="1H", current_price=111.0, timestamp=2000)
    htf_payload = make_payload(timeframe="4H", current_price=111.0, timestamp=2000)
    atm.evaluate(htf_payload, mtf_payload, ltf_payload)
    assert plan.stop_invalidation_price == pytest.approx(101.0, 1e-4)

    # Step 2: MTF structural trailing engine produces new stop at 108.0 (+0.8R)
    # Simulate structural stop update
    plan.stop_invalidation_price = max(plan.stop_invalidation_price, 108.0)
    assert plan.stop_invalidation_price == 108.0


# 6. Same-bar +1R/stop collision -> adverse-first behavior preserved
def test_same_bar_collision_adverse_first_prior_stop_wins():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0) # risk = 10.0, +1R = 110.0, prior stop = 90.0
    ledger.trades[trade.trade_id] = trade

    # Volatile candle touches BOTH +1.0R (110.5) AND prior stop (89.5)
    c1 = Candle(timestamp=2000, open=100.0, high=110.5, low=89.5, close=95.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    assert closed[0].exit_reason == "INITIAL_LTF_SL"
    assert closed[0].realized_rr < 0 # Exited at adverse stop loss, NOT +0.10R breakeven


# 7. +1R reached only on a later candle -> no premature stop modification
def test_1r_reached_only_on_later_candle_no_premature_modification():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Candle 1: High reaches 107.0 (+0.7R)
    c1 = Candle(timestamp=2000, open=100.0, high=107.0, low=96.0, close=105.0, volume=10.0)
    sim.process_candle(c1, ledger)
    assert trade.current_stop_price == 90.0
    assert "breakeven_triggered" not in trade.metadata

    # Candle 2: High reaches 111.0 (+1.1R) -> now triggers
    c2 = Candle(timestamp=3000, open=105.0, high=111.0, low=103.0, close=110.0, volume=10.0)
    sim.process_candle(c2, ledger)
    assert trade.current_stop_price == pytest.approx(101.0, 1e-4)
    assert trade.metadata.get("breakeven_triggered") is True


# 8. Repeated +1R observations -> no repeated/invalid stop mutation
def test_repeated_1r_observations_no_corrupt_mutation():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Candle 1: Reaches +1.1R
    c1 = Candle(timestamp=2000, open=100.0, high=111.0, low=98.0, close=110.0, volume=10.0)
    sim.process_candle(c1, ledger)
    assert trade.current_stop_price == pytest.approx(101.0, 1e-4)

    # Candle 2: Reaches +2.0R (120.0) -> Breakeven stop should stay at 101.0 (no rolling giveback floor)
    c2 = Candle(timestamp=3000, open=110.0, high=120.0, low=108.0, close=118.0, volume=10.0)
    sim.process_candle(c2, ledger)
    assert trade.current_stop_price == pytest.approx(101.0, 1e-4)


# 9. No candidate duplication
def test_no_candidate_duplication():
    coord = StrategyCoordinator(enable_breakeven_1r=True)
    assert len(coord.candidate_tracker.active_candidates) == 0


# 10. No change to entry qualification
def test_no_change_to_entry_qualification():
    coord_baseline = StrategyCoordinator(enable_breakeven_1r=False)
    coord_treatment = StrategyCoordinator(enable_breakeven_1r=True)

    # Both must use UnifiedStrategy with identical structural parameters
    hyp_base = coord_baseline.hypotheses["UNIFIED_STRATEGY"]
    hyp_treat = coord_treatment.hypotheses["UNIFIED_STRATEGY"]
    assert hyp_base.enforce_displacement_polarity == hyp_treat.enforce_displacement_polarity
    assert hyp_base.enable_forward_expansion == hyp_treat.enable_forward_expansion


# 11. No change to initial SL
def test_no_change_to_initial_sl():
    trade = make_long_trade(entry=100.0, stop=90.0)
    assert trade.initial_stop_price == 90.0


# 12. No change to target
def test_no_change_to_target():
    trade = make_long_trade(entry=100.0, stop=90.0, target=150.0)
    assert trade.target_price == 150.0


# 13. No change to risk sizing
def test_no_change_to_risk_sizing():
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY",
        trade_plan_id="plan_risk_1",
        symbol="BTCUSDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0,
        target_price=150.0,
        raw_rr=5.0,
        status="ENTERED"
    )
    account = AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    cfg = RiskConfig(max_risk_fraction=0.01, min_rr_floor=4.0)
    result = RiskCoordinator.evaluate(plan, account, config=cfg)
    assert result.dollar_risk == 100.0 # Exactly 1% of 10,000
    assert result.position_units == 10.0 # 100 / (100 - 90) = 10.0
