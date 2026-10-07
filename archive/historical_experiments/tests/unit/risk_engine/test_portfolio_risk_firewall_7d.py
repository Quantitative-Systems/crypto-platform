"""
Unit tests for QCP 7-Dimensional Portfolio Risk Firewall.
Tests comprehensive veto capabilities across Market, Liquidity, Correlation,
Execution, Exchange, Model, and Tail Risk dimensions.
"""

import pytest
from risk_engine.portfolio_risk_firewall import (
    PortfolioRiskFirewall,
    FirewallThresholds,
    FirewallAction,
    DimensionStatus,
)


@pytest.fixture
def firewall():
    return PortfolioRiskFirewall()


def test_firewall_nominal_approval(firewall):
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
    )

    assert decision.action == FirewallAction.APPROVE
    assert decision.risk_multiplier == 1.0
    assert len(decision.rejection_reasons) == 0
    for dim_name, dim_eval in decision.dimensions.items():
        assert dim_eval.status == DimensionStatus.PASS


def test_market_risk_gross_leverage_rejection(firewall):
    # Trying to open a $3,500 position on a $1,000 account (3.5x leverage > 3.0x limit)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=3500.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.risk_multiplier == 0.0
    assert decision.dimensions["market_risk"].status == DimensionStatus.FAIL
    assert any("Gross leverage" in r for r in decision.rejection_reasons)


def test_liquidity_risk_spread_rejection(firewall):
    # Spread is 0.25% (25 bps > 15 bps limit)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
        market_metrics={"spread_pct": 0.0025, "book_depth_usd": 50000.0},
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["liquidity_risk"].status == DimensionStatus.FAIL
    assert any("Market spread" in r for r in decision.rejection_reasons)


def test_correlation_risk_clustering_rejection(firewall):
    # Two existing long positions with $14.0 risk ($1000 account -> 1.4% heat)
    # Adding a $6.0 long risk pushes correlated long heat to 2.0% (> 1.8% limit)
    open_positions = [
        {"symbol": "BTC/USDT", "direction": "BUY", "risk_usd": 8.0, "notional_usd": 200.0},
        {"symbol": "ETH/USDT", "direction": "LONG", "risk_usd": 6.0, "notional_usd": 150.0},
    ]

    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=open_positions,
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["correlation_risk"].status == DimensionStatus.FAIL
    assert any("Correlated directional heat" in r for r in decision.rejection_reasons)


def test_execution_risk_stale_feed_rejection(firewall):
    # Feed is 45 seconds old (> 30s limit)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
        execution_metrics={"stale_sec": 45.0, "latency_ms": 100.0},
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["execution_risk"].status == DimensionStatus.FAIL
    assert any("Price feed stale" in r for r in decision.rejection_reasons)


def test_exchange_risk_abnormal_funding_rejection(firewall):
    # Funding rate is 35 bps (indicates liquidation squeeze)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
        exchange_metrics={"funding_rate_bps": 35.0, "is_exchange_degraded": False},
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["exchange_risk"].status == DimensionStatus.FAIL
    assert any("Extreme funding rate" in r for r in decision.rejection_reasons)


def test_model_risk_degradation_rejection(firewall):
    # Strategy drift score is 0.60 (> 0.40) and rolling expectancy is -0.20R (< -0.15R)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
        model_metrics={"drift_score": 0.60, "rolling_expectancy_r": -0.20},
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["model_risk"].status == DimensionStatus.FAIL
    assert any("Strategy drift score" in r for r in decision.rejection_reasons)


def test_tail_risk_drawdown_halt_and_flash_crash(firewall):
    # Account is down 7.0% from peak ($1,000 peak -> $930 current equity)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=150.0,
        account_equity_usd=930.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
    )

    assert decision.action == FirewallAction.REJECT
    assert decision.dimensions["tail_risk"].status == DimensionStatus.FAIL
    assert any("Account in max drawdown state" in r for r in decision.rejection_reasons)


def test_elevated_risk_reduction(firewall):
    # Near threshold (e.g. leverage 2.6x on a 3.0x limit -> score 0.867 > 0.8)
    decision = firewall.evaluate_order(
        candidate_symbol="SOL/USDT",
        candidate_direction="BUY",
        intended_risk_usd=6.0,
        intended_notional_usd=2600.0,
        account_equity_usd=1000.0,
        current_peak_equity_usd=1000.0,
        open_positions=[],
    )

    assert decision.action == FirewallAction.APPROVE_REDUCED_RISK
    assert decision.risk_multiplier == 0.50
    assert decision.dimensions["market_risk"].status == DimensionStatus.WARN
