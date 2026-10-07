"""Unit tests for STRATA Adversarial Risk Hardening & Invariant Defenses."""
import pytest
from execution.decision.phase_r_decision_engine import (
    DecisionType,
    PhaseRDecisionEngine,
)
from execution.portfolio.risk_governor import (
    PortfolioOpportunity,
    PortfolioRiskGovernor,
)


def test_inverted_target_geometry_adversarially_rejected():
    engine = PhaseRDecisionEngine(symbol="BTCUSDT", initial_equity_usd=100_000.0)

    # Long with Stop > Entry (Inverted Geometry)
    is_valid, planned_r, reasons = engine.validate_target_geometry(
        direction=1,
        entry=60000.0,
        stop=61000.0,  # Invalid! Stop > Entry
        target=65000.0,
    )
    assert not is_valid
    assert "INVALID_TARGET_GEOMETRY" in reasons

    # Short with Stop < Entry (Inverted Geometry)
    is_valid_short, planned_r_short, reasons_short = engine.validate_target_geometry(
        direction=-1,
        entry=60000.0,
        stop=59000.0,  # Invalid! Stop < Entry
        target=50000.0,
    )
    assert not is_valid_short
    assert "INVALID_TARGET_GEOMETRY" in reasons_short


def test_sub_4r_target_floor_adversarially_rejected():
    engine = PhaseRDecisionEngine(symbol="ETHUSDT", initial_equity_usd=100_000.0)

    # Valid geometry, but only 2.5R (Less than required 4.0R floor)
    is_valid, planned_r, reasons = engine.validate_target_geometry(
        direction=1,
        entry=3000.0,
        stop=2900.0,   # Risk: $100
        target=3250.0, # Reward: $250 -> 2.5R
    )
    assert not is_valid
    assert "TARGET_BELOW_4R" in reasons


def test_correlated_portfolio_opportunity_haircut():
    gov = PortfolioRiskGovernor(
        max_total_portfolio_risk_pct=0.03,
        max_single_trade_risk_pct=0.01,
        high_correlation_threshold=0.75,
        correlation_haircut_factor=0.50,
    )
    assert gov.is_correlated_with_active("BTCUSDT", "ETHUSDT")
    assert gov.is_correlated_with_active("BTCUSDT", "SOLUSDT")
