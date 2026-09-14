"""
Unit tests for Production Trade Management Lifecycle Engine.
"""

import pytest
from trade_management.lifecycle_engine import (
    TradeManagementEngine,
    TradeOrderPlan,
    OrderType,
    PositionLifecycleStage,
)


def test_pre_entry_checks_spread_and_heat():
    engine = TradeManagementEngine()
    plan = TradeOrderPlan(
        symbol="SOLUSDT",
        direction="LONG",
        order_type=OrderType.LIMIT,
        intended_entry_price=100.0,
        intended_sl_price=96.50,
        intended_tp1_price=103.50,
        intended_tp2_price=107.00,
        intended_tp3_price=110.50,
        intended_qty=1.714,
        intended_notional=171.4,
        risk_usd=6.0,
        risk_pct_account=0.60,
    )

    # 1. Clean conditions
    res_clean = engine.perform_pre_entry_checks(
        plan=plan,
        current_bid=99.98,
        current_ask=100.02,
        current_atr=3.0,
        account_equity=1000.0,
        current_portfolio_heat_pct=1.0,
    )
    assert res_clean.passed is True
    assert len(res_clean.rejection_reasons) == 0

    # 2. Excessive spread (>0.15%)
    res_wide_spread = engine.perform_pre_entry_checks(
        plan=plan,
        current_bid=99.80,
        current_ask=100.20,  # 0.40% spread
        current_atr=3.0,
        account_equity=1000.0,
        current_portfolio_heat_pct=1.0,
    )
    assert res_wide_spread.passed is False
    assert any("Spread" in r for r in res_wide_spread.rejection_reasons)

    # 3. Excessive heat (>3.0%)
    res_high_heat = engine.perform_pre_entry_checks(
        plan=plan,
        current_bid=99.98,
        current_ask=100.02,
        current_atr=3.0,
        account_equity=1000.0,
        current_portfolio_heat_pct=2.70,  # 2.70% + 0.60% = 3.30% > 3.0%
    )
    assert res_high_heat.passed is False
    assert any("heat" in r for r in res_high_heat.rejection_reasons)


def test_trade_lifecycle_tp_and_trailing():
    engine = TradeManagementEngine()
    pos = engine.initialize_position(
        position_id="POS-SOL-1",
        strategy_id="FAM-07-SOL",
        symbol="SOLUSDT",
        direction="LONG",
        fill_price=100.0,
        fill_qty=2.0,
        initial_sl=96.0,  # 1R = $4.00
        tp1_price=104.0,  # +1R
        tp2_price=108.0,  # +2R
        tp3_price=112.0,  # +3R
        timestamp=1000,
    )
    assert pos.stage == PositionLifecycleStage.ACTIVE
    assert pos.current_sl_price == 96.0

    # Bar 1: Price hits TP1 (High=104.5) -> Break-even lock, 50% scale out
    up1 = engine.update_position_bar(
        position_id="POS-SOL-1",
        current_high=104.5,
        current_low=100.2,
        current_close=103.5,
        current_atr=3.0,
        timestamp=1100,
    )
    assert pos.tp1_hit is True
    assert pos.current_sl_price == 100.0  # Break-even
    assert pos.remaining_qty == 1.0  # 50% scaled out
    assert pos.stage == PositionLifecycleStage.BREAK_EVEN_LOCKED

    # Bar 2: Price hits TP2 (High=108.5) -> SL moved to +1R ($104), another 25% scaled out
    up2 = engine.update_position_bar(
        position_id="POS-SOL-1",
        current_high=108.5,
        current_low=103.0,
        current_close=107.0,
        current_atr=3.0,
        timestamp=1200,
    )
    assert pos.tp2_hit is True
    assert pos.current_sl_price == 104.0  # +1R locked
    assert pos.remaining_qty == 0.5

    # Bar 3: Price hits TP3 (High=113.0) -> Position closed with full profit
    up3 = engine.update_position_bar(
        position_id="POS-SOL-1",
        current_high=113.0,
        current_low=106.0,
        current_close=112.5,
        current_atr=3.0,
        timestamp=1300,
    )
    assert up3["action"] == "FULL_TP3_EXIT"
    assert "POS-SOL-1" not in engine.active_positions
