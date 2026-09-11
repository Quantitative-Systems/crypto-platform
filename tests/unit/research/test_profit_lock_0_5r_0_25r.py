"""
Unit tests for PROFIT_LOCK_0.5R_0.25R research experiment.
Validates the mandatory causal invariants:
1. LONG reaches +0.5R -> stop moves to +0.25R.
2. SHORT reaches +0.5R -> stop moves to -0.25R.
3. Price never reaches +0.5R -> stop remains unchanged.
4. Existing stop is already better than +0.25R -> monotonicity: do not weaken it.
5. Adverse-first same-bar collision: candle touches BOTH +0.5R AND prior stop -> prior adverse stop wins (exits at initial SL, profit lock does not trigger).
6. Causal same-bar protection guard: candle reaches +0.5R, stop ratchets to +0.25R, low is <= +0.25R BUT close is > +0.25R -> trade survives candle t. On candle t+1, if low touches <= +0.25R, it exits at +0.25R with exit_reason PROFIT_LOCK_TRAIL.
7. Trigger bar close-through: candle reaches +0.5R, stop ratchets to +0.25R, and candle closes <= +0.25R -> trade exits on candle t at candle.close with exit_reason PROFIT_LOCK_TRAIL.
8. Canonical H0 defaults preserved: enable_profit_lock=False leaves stops unchanged at +0.5R.
"""

import pytest
from market_intelligence.primitives import Candle
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


# 1. LONG reaches +0.5R -> stop moves to +0.25R
def test_long_reaches_0_5r_moves_stop_to_plus_0_25r():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)  # risk = 10.0, +0.5R = 105.0, +0.25R = 102.5
    ledger.trades[trade.trade_id] = trade

    # Bar 1: Price reaches 105.5 (+0.55R >= +0.5R), low stays at 98.0 (> 90.0), close at 104.0 (> 102.5)
    c1 = Candle(timestamp=2000, open=100.0, high=105.5, low=98.0, close=104.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == pytest.approx(102.5, 1e-4)
    assert trade.metadata.get("profit_locked") is True
    assert trade.metadata.get("profit_lock_stop_price") == pytest.approx(102.5, 1e-4)


# 2. SHORT reaches +0.5R -> stop moves to -0.25R
def test_short_reaches_0_5r_moves_stop_to_minus_0_25r():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_short_trade(entry=100.0, stop=110.0)  # risk = 10.0, +0.5R = 95.0, floor stop = 97.5
    ledger.trades[trade.trade_id] = trade

    # Bar 1: Price drops to 94.5 (+0.55R favorable excursion), high stays at 102.0 (< 110.0), close at 96.0 (< 97.5)
    c1 = Candle(timestamp=2000, open=100.0, high=102.0, low=94.5, close=96.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == pytest.approx(97.5, 1e-4)
    assert trade.metadata.get("profit_locked") is True
    assert trade.metadata.get("profit_lock_stop_price") == pytest.approx(97.5, 1e-4)


# 3. Price never reaches +0.5R -> stop remains unchanged
def test_price_never_reaches_0_5r_stop_unchanged():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Bar reaches +0.4R (104.0)
    c1 = Candle(timestamp=2000, open=100.0, high=104.0, low=95.0, close=103.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == 90.0
    assert "profit_locked" not in trade.metadata


# 4. Existing stop is already better than +0.25R -> do not weaken it
def test_existing_stop_already_better_does_not_weaken():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)
    trade.current_stop_price = 106.0  # Already trailed to +0.60R
    ledger.trades[trade.trade_id] = trade

    # Bar reaches +0.8R (108.0)
    c1 = Candle(timestamp=2000, open=106.0, high=108.0, low=106.0, close=107.0, volume=10.0)
    sim.process_candle(c1, ledger)

    # Stop must remain at 106.0 and NOT be downgraded to 102.5
    assert trade.current_stop_price == 106.0


# 5. Adverse-first collision on trigger candle: prior adverse stop wins
def test_same_bar_collision_adverse_first_prior_stop_wins():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)  # risk = 10.0, +0.5R = 105.0, prior stop = 90.0
    ledger.trades[trade.trade_id] = trade

    # Volatile candle touches BOTH +0.5R (106.0) AND prior stop (89.0)
    c1 = Candle(timestamp=2000, open=100.0, high=106.0, low=89.0, close=95.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    assert closed[0].exit_reason == "INITIAL_LTF_SL"
    assert closed[0].realized_rr < 0  # Exited at adverse stop loss, NOT +0.25R profit lock


# 6. Causal same-bar protection guard: candle reaches +0.5R, low is <= +0.25R, close > +0.25R -> trade survives candle t
def test_causal_same_bar_guard_trade_survives_when_close_above_stop():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)  # risk = 10.0, +0.5R = 105.0, +0.25R = 102.5
    ledger.trades[trade.trade_id] = trade

    # Candle 1: Open=100, High=106.0 (+0.6R), Low=101.0 (below new stop 102.5, but above initial SL 90.0), Close=105.0 (> 102.5)
    c1 = Candle(timestamp=2000, open=100.0, high=106.0, low=101.0, close=105.0, volume=10.0)
    closed_1 = sim.process_candle(c1, ledger)

    # Must NOT exit on candle 1 because close was above new stop!
    assert len(closed_1) == 0
    assert trade.status == "ACTIVE"
    assert trade.current_stop_price == pytest.approx(102.5, 1e-4)

    # Candle 2: Open=105, High=105.5, Low=102.0 (hits active stop 102.5), Close=103.0
    c2 = Candle(timestamp=3000, open=105.0, high=105.5, low=102.0, close=103.0, volume=10.0)
    closed_2 = sim.process_candle(c2, ledger)

    # Now cleanly exits on candle 2 at the protected floor!
    assert len(closed_2) == 1
    assert closed_2[0].exit_reason == "PROFIT_LOCK_TRAIL"
    assert closed_2[0].realized_rr > 0  # Exited with protected profit


# 7. Trigger bar close-through: candle reaches +0.5R and closes through +0.25R -> exits on candle t at candle close
def test_trigger_bar_close_through_exits_at_close():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=True, profit_lock_trigger_r=0.5, profit_lock_stop_r=0.25)
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Candle 1: Rallies to 106.0 (+0.6R), then collapses to close at 101.0 (<= 102.5 stop floor)
    c1 = Candle(timestamp=2000, open=100.0, high=106.0, low=98.0, close=101.0, volume=10.0)
    closed = sim.process_candle(c1, ledger)

    assert len(closed) == 1
    assert closed[0].exit_reason == "PROFIT_LOCK_TRAIL"


# 8. Canonical H0 defaults preserved
def test_h0_default_leaves_stop_unchanged():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_profit_lock=False)  # Canonical H0 default
    trade = make_long_trade(entry=100.0, stop=90.0)
    ledger.trades[trade.trade_id] = trade

    # Candle 1 reaches +0.8R (108.0)
    c1 = Candle(timestamp=2000, open=100.0, high=108.0, low=98.0, close=107.0, volume=10.0)
    sim.process_candle(c1, ledger)

    # Stop must remain at initial SL of 90.0
    assert trade.current_stop_price == 90.0
    assert "profit_locked" not in trade.metadata
