"""
Unit Tests for Product 04: Execution & Friction Simulator
"""

import pytest
from market_intelligence.primitives import Candle
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator


def make_candle(ts: int, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(timestamp=ts, open=o, high=h, low=l, close=c, volume=10.0)


def test_limit_entry_and_tp_exit():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(maker_fee_rate=0.0, taker_fee_rate=0.0005, slippage_bps=5.0)

    trade = SimulatedTrade(
        trade_id="trade-1",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=140.0,
        position_units=10.0,
        dollar_risk=100.0,
        raw_rr=4.0
    )
    ledger.record_pending_trade(trade)

    # Bar 1: Price reaches 99.0 -> triggers limit entry at 100.0
    bar1 = make_candle(2000, 102.0, 103.0, 99.0, 101.0)
    closed = sim.process_candle(bar1, ledger)
    assert len(closed) == 0
    assert trade.status == "ACTIVE"
    assert trade.fill_entry_price == 100.0

    # Bar 2: Price reaches 142.0 -> triggers Take Profit at 140.0
    bar2 = make_candle(3000, 105.0, 142.0, 104.0, 139.0)
    closed = sim.process_candle(bar2, ledger)
    assert len(closed) == 1
    assert closed[0].exit_reason == "HTF_TP"
    assert closed[0].exit_price == 140.0
    assert closed[0].realized_pnl == (140.0 - 100.0) * 10.0  # 400.0
    assert closed[0].realized_rr == 4.0
    assert ledger.current_equity == 10400.0


def test_adverse_first_collision_resolution():
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(maker_fee_rate=0.0, taker_fee_rate=0.0005, slippage_bps=5.0)

    trade = SimulatedTrade(
        trade_id="trade-2",
        hypothesis_id="HYP_B_CONTINUATION_RIDING",
        symbol="ETHUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=2000.0,
        initial_stop_price=1900.0,
        current_stop_price=1900.0,
        target_price=2400.0,
        position_units=1.0,
        dollar_risk=100.0,
        raw_rr=4.0,
        status="ACTIVE",
        fill_entry_price=2000.0
    )
    ledger.trades[trade.trade_id] = trade

    # Flash Crash & Spike Bar: Low = 1850 (breaches SL 1900), High = 2450 (breaches TP 2400)
    ambiguous_bar = make_candle(2000, 2000.0, 2450.0, 1850.0, 2100.0)
    closed = sim.process_candle(ambiguous_bar, ledger)

    # Adverse-first axiom: Stop Loss MUST execute, NOT Take Profit
    assert len(closed) == 1
    assert closed[0].exit_reason == "INITIAL_LTF_SL"
    # Stop price 1900 with selling slippage: 1900 * (1 - 0.0005) = 1899.05
    assert closed[0].exit_price == pytest.approx(1899.05, rel=1e-3)
    assert closed[0].realized_pnl < 0.0
