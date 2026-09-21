"""
Unit tests for ExecutionSimulator exact execution physics, collision resolution, and fee/slippage modeling.
"""

import pytest
from market_intelligence.primitives import Candle
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator


def test_maker_limit_entry_fill():
    """Limit buy entry triggers when candle.low <= entry_price, filled at exact limit price with maker fee."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(maker_fee_rate=0.0000, taker_fee_rate=0.0005, slippage_bps=5.0)

    trade = SimulatedTrade(
        trade_id="t_entry_1",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=150.0,
        position_units=10.0,
        dollar_risk=100.0,
        status="PENDING_ENTRY"
    )
    ledger.record_pending_trade(trade)

    # Candle 1: Low is 101.0 -> No fill
    c1 = Candle(timestamp=2000, open=105.0, high=106.0, low=101.0, close=103.0, volume=10.0)
    sim.process_candle(c1, ledger)
    assert trade.status == "PENDING_ENTRY"

    # Candle 2: Low is 99.0 -> Fills at exact limit 100.0
    c2 = Candle(timestamp=3000, open=103.0, high=104.0, low=99.0, close=101.0, volume=10.0)
    sim.process_candle(c2, ledger)
    assert trade.status == "ACTIVE"
    assert trade.fill_entry_price == 100.0
    assert trade.entry_fee == 0.0
    assert trade.entry_slippage_bps == 0.0


def test_adverse_first_collision_resolution():
    """
    When both Stop Loss and Take Profit levels are reached within the same bar,
    adverse-first execution forces the Stop Loss to trigger first.
    """
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(maker_fee_rate=0.0000, taker_fee_rate=0.0005, slippage_bps=5.0)

    trade = SimulatedTrade(
        trade_id="t_coll_1",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        fill_entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=150.0,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )
    ledger.trades[trade.trade_id] = trade

    # Ambiguous wide candle: Low penetrates SL (85.0 <= 90.0) AND High penetrates TP (160.0 >= 150.0)
    ambiguous_bar = Candle(timestamp=2000, open=100.0, high=160.0, low=85.0, close=110.0, volume=100.0)
    closed_trades = sim.process_candle(ambiguous_bar, ledger)

    assert len(closed_trades) == 1
    closed = closed_trades[0]
    # Must exit as Stop Loss, NOT as Take Profit
    assert closed.exit_reason == "INITIAL_LTF_SL"
    # Stop loss applies adverse slippage (5 bps = 0.05% on 90.0 -> 89.955)
    assert closed.exit_price < 90.0
    assert closed.realized_pnl < 0


def test_profit_lock_ratchet_execution():
    """
    When profit lock is enabled and MFE reaches +1.5R, stop is ratcheted to break-even (+0.1R buffer).
    """
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(
        maker_fee_rate=0.0,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75
    )

    trade = SimulatedTrade(
        trade_id="t_pl_1",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        fill_entry_price=100.0,
        initial_stop_price=90.0,  # 1.0R = 10.0
        current_stop_price=90.0,
        target_price=150.0,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )
    ledger.trades[trade.trade_id] = trade

    # Bar 1: Price rallies to 116.0 (+1.6R MFE) with low staying high (110.0) -> Ratchets profit lock
    c1 = Candle(timestamp=2000, open=105.0, high=116.0, low=110.0, close=115.0, volume=50.0)
    sim.process_candle(c1, ledger)

    # Stop should now be ratcheted above initial stop (to break-even + 0.1R = 101.0, or trailed floor)
    assert trade.current_stop_price >= 101.0
    assert trade.metadata.get("profit_locked") is True

    # Bar 2: Price drops back to 100.0 -> Triggers profit lock stop exit
    c2 = Candle(timestamp=3000, open=115.0, high=115.0, low=99.0, close=100.0, volume=50.0)
    closed = sim.process_candle(c2, ledger)

    assert len(closed) == 1
    assert closed[0].exit_reason == "PROFIT_LOCK_TRAIL"
    assert closed[0].realized_rr > 0  # Protected small profit rather than full 1.0R loss
