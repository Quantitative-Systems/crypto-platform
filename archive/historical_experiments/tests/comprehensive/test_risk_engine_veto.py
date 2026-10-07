"""
Comprehensive Test Suite: Unified Risk Engine & Sovereign Veto.
Validates:
- Pre-trade risk gate evaluation
- Hard 3.00% portfolio heat ceiling
- Price collars
- Sovereign Kill Switch (Emergency Halt, Hard Kill, Reset)
"""

import pytest
from risk_engine.unified_risk_engine import (
    UnifiedRiskEngine,
    PreTradeOrderSpec,
    KillSwitchState,
)
from risk_engine.portfolio_risk_firewall import FirewallAction


@pytest.fixture
def risk_engine():
    return UnifiedRiskEngine()


def test_pre_trade_risk_normal_approval(risk_engine):
    order = PreTradeOrderSpec(
        strategy_id="FAM-07-TEST",
        symbol="BTCUSDT",
        order_type="LIMIT",
        direction="BUY",
        quantity=0.05,
        limit_price=60_000.0,
        notional_usd=3_000.0,
        current_market_price=60_000.0,
        stop_loss_price=59_000.0,
        account_equity_usd=100_000.0,
    )
    result = risk_engine.evaluate_pre_trade_risk(
        order=order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=1.0,
    )
    assert result.approved is True
    assert result.risk_action == FirewallAction.APPROVE
    assert result.allocated_quantity == 0.05


def test_pre_trade_risk_heat_ceiling_breach(risk_engine):
    order = PreTradeOrderSpec(
        strategy_id="FAM-07-TEST",
        symbol="BTCUSDT",
        order_type="LIMIT",
        direction="BUY",
        quantity=1.0,
        limit_price=60_000.0,
        notional_usd=60_000.0,
        current_market_price=60_000.0,
        stop_loss_price=50_000.0,  # 16.6% risk = $10,000 risk on $100k equity = 10% incremental heat
        account_equity_usd=100_000.0,
    )
    result = risk_engine.evaluate_pre_trade_risk(
        order=order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=2.5,
    )
    assert result.approved is False
    assert result.risk_action == FirewallAction.REJECT
    assert any("ceiling" in r.lower() for r in result.rejection_reasons)


def test_price_collar_rejection(risk_engine):
    order = PreTradeOrderSpec(
        strategy_id="FAM-07-TEST",
        symbol="BTCUSDT",
        order_type="LIMIT",
        direction="BUY",
        quantity=0.01,
        limit_price=65_000.0,  # +8.3% deviation from market 60,000 (exceeds 3% collar)
        notional_usd=650.0,
        current_market_price=60_000.0,
        account_equity_usd=100_000.0,
    )
    result = risk_engine.evaluate_pre_trade_risk(
        order=order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=0.5,
    )
    assert result.approved is False
    assert any("deviates" in r.lower() for r in result.rejection_reasons)


def test_kill_switch_veto_authority(risk_engine):
    order = PreTradeOrderSpec(
        strategy_id="FAM-07-TEST",
        symbol="BTCUSDT",
        order_type="LIMIT",
        direction="BUY",
        quantity=0.01,
        limit_price=60_000.0,
        notional_usd=600.0,
        current_market_price=60_000.0,
        account_equity_usd=100_000.0,
    )

    # 1. Trigger Emergency Halt
    risk_engine.trigger_emergency_halt("Anomalous volatility spike detected")
    assert risk_engine.kill_switch_state == KillSwitchState.EMERGENCY_HALT

    # Order must be vetoed immediately
    result = risk_engine.evaluate_pre_trade_risk(
        order=order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=0.5,
    )
    assert result.approved is False
    assert "Kill Switch Active" in result.rejection_reasons[0]

    # 2. Reset Kill Switch
    success = risk_engine.reset_kill_switch("CLEAR-RISK-ADMIN-KEY")
    assert success is True
    assert risk_engine.kill_switch_state == KillSwitchState.ARMED_NORMAL

    # Now order should be approved
    result_after = risk_engine.evaluate_pre_trade_risk(
        order=order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=0.5,
    )
    assert result_after.approved is True


def test_small_account_economic_viability_veto(risk_engine):
    """
    Directive EABG-001: A $100 account cannot safely absorb exchange minimum lot sizes
    and transaction friction. The system must explicitly return 'INSUFFICIENT CAPITAL / NO TRADE'.
    """
    small_order = PreTradeOrderSpec(
        strategy_id="FAM-01-TREND",
        symbol="BTCUSDT",
        order_type="LIMIT",
        direction="BUY",
        quantity=0.001,
        limit_price=60_000.0,
        notional_usd=60.0,
        current_market_price=60_000.0,
        stop_loss_price=58_800.0,  # 2% stop = $1.20 risk
        account_equity_usd=100.0,  # $100 account
    )

    # 1. Test standalone economic viability evaluation
    viability = risk_engine.evaluate_account_economic_viability(small_order)
    assert viability.is_viable is False
    assert viability.verdict == "INSUFFICIENT CAPITAL / NO TRADE"
    assert "below minimum viable threshold" in viability.rejection_reason

    # 2. Test pre-trade risk veto
    result = risk_engine.evaluate_pre_trade_risk(
        order=small_order,
        current_open_positions=[],
        current_drawdown_pct=0.0,
        current_portfolio_heat_pct=0.0,
    )
    assert result.approved is False
    assert result.risk_action == FirewallAction.REJECT
    assert any("INSUFFICIENT CAPITAL / NO TRADE" in r for r in result.rejection_reasons)

