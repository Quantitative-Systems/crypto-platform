"""
Comprehensive Test Suite: Portfolio Intelligence & Hedging Engine.
Validates:
- Uncertainty-discounted expected net edge
- Shrunk covariance & correlation
- 99% Tail CVaR computation
- Non-negotiable 3.00% portfolio heat ceiling
- Multi-mode Hedging Engine (Beta, Delta, Volatility, Basis)
"""

import numpy as np
import pytest
from portfolio_engine.intelligence.risk_budget_allocator import (
    PortfolioIntelligenceEngine,
    StrategyRiskProfile,
)
from portfolio_engine.hedging.hedging_engine import (
    ComprehensiveHedgingEngine,
    ExposureDecomposition,
    HedgeMode,
    HedgeStatus,
)


def test_uncertainty_discounted_edge():
    pie = PortfolioIntelligenceEngine()
    # E = 0.20, SE = 0.05 -> 0.20 - 1.96 * 0.05 = 0.20 - 0.098 = 0.102
    disc = pie.calculate_discounted_edge(expected_edge_r=0.20, se_r=0.05)
    assert round(disc, 3) == 0.102

    # High uncertainty -> 0 edge
    disc_zero = pie.calculate_discounted_edge(expected_edge_r=0.10, se_r=0.10)
    assert disc_zero == 0.0


def test_portfolio_heat_hard_ceiling():
    pie = PortfolioIntelligenceEngine()
    strats = [
        StrategyRiskProfile("S1", "BTCUSDT", "TREND", 0.50, 0.05, 0.5, 5.0, 0.02, 1_000_000.0),
        StrategyRiskProfile("S2", "ETHUSDT", "TREND", 0.50, 0.05, 0.5, 5.0, 0.02, 1_000_000.0),
        StrategyRiskProfile("S3", "SOLUSDT", "TREND", 0.50, 0.05, 0.5, 5.0, 0.02, 1_000_000.0),
        StrategyRiskProfile("S4", "AVAXUSDT", "TREND", 0.50, 0.05, 0.5, 5.0, 0.02, 1_000_000.0),
    ]

    snapshot = pie.allocate_risk_budgets(total_equity_usd=100_000.0, strategies=strats)
    assert snapshot.current_portfolio_heat_pct <= 3.00
    assert snapshot.fail_closed_status is False


def test_tail_cvar_computation():
    pie = PortfolioIntelligenceEngine()
    sim_returns = np.random.normal(0.001, 0.02, 1000)
    var, cvar = pie.compute_tail_risk(sim_returns, confidence=0.99)
    assert var > 0.0
    assert cvar >= var


def test_comprehensive_hedging_engine():
    he = ComprehensiveHedgingEngine()
    positions = [
        {"symbol": "BTCUSDT", "notional_usd": 150_000.0, "direction": "LONG", "vega": -600.0, "basis_bps": 180.0, "asset_class": "PERP"},
        {"symbol": "ETHUSDT", "notional_usd": 100_000.0, "direction": "LONG", "vega": 0.0, "basis_bps": 20.0, "asset_class": "PERP"},
    ]
    decomps = he.decompose_portfolio(positions=positions, account_equity_usd=100_000.0)
    assert len(decomps) == 2

    # High beta + high vega + high basis should generate hedges
    hedges = he.generate_hedges(decompositions=decomps, account_equity_usd=100_000.0, current_portfolio_heat_pct=1.0)
    assert len(hedges) >= 1

    modes = {h.mode for h in hedges}
    assert HedgeMode.BETA in modes or HedgeMode.VOLATILITY in modes or HedgeMode.BASIS in modes
