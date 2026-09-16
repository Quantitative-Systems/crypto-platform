"""
Tests for Autonomous Risk Governor.
"""

from risk_engine.autonomous_risk_governor import (
    AutonomousRiskGovernor,
    RiskVetoDecision,
)


def test_risk_governor_approval_and_vetoes():
    governor = AutonomousRiskGovernor(
        max_portfolio_heat_pct=3.0,
        max_strategy_risk_pct=1.5,
        max_spread_multiplier=3.0
    )

    # 1. Healthy trade approved
    dec = governor.evaluate_order_risk(
        alpha_id="FAM-07",
        symbol="SOL/USDT",
        proposed_risk_usd=100.0,
        portfolio_equity_usd=10_000.0,
        current_open_risk_usd=0.0,
        current_drawdown_pct=0.0,
        current_spread_bps=2.0,
        normal_spread_bps=2.0
    )
    assert dec.is_approved is True
    assert dec.veto_reason is None
    assert dec.approved_risk_usd == 100.0

    # 2. Spread blowout veto
    dec_spread = governor.evaluate_order_risk(
        alpha_id="FAM-07",
        symbol="SOL/USDT",
        proposed_risk_usd=100.0,
        portfolio_equity_usd=10_000.0,
        current_open_risk_usd=0.0,
        current_drawdown_pct=0.0,
        current_spread_bps=10.0,  # 5x normal
        normal_spread_bps=2.0
    )
    assert dec_spread.is_approved is False
    assert dec_spread.veto_reason == "VETO_SPREAD_BLOWOUT"
    assert dec_spread.approved_risk_usd == 0.0

    # 3. Portfolio heat ceiling veto
    dec_heat = governor.evaluate_order_risk(
        alpha_id="FAM-07",
        symbol="SOL/USDT",
        proposed_risk_usd=100.0,
        portfolio_equity_usd=10_000.0,
        current_open_risk_usd=300.0,  # 3.0% already open
        current_drawdown_pct=0.0
    )
    assert dec_heat.is_approved is False
    assert dec_heat.veto_reason == "VETO_PORTFOLIO_HEAT_CEILING_REACHED"
