"""Unit tests for PortfolioEngine allocation, concentration caps, and stress testing."""
import pytest
from crypto_platform.portfolio_engine import (
    PortfolioConstraints,
    PortfolioEngine,
    PortfolioMetrics,
)


@pytest.fixture
def mock_strategy_stats():
    return {
        "CARRY_BTC": {
            "horizon": "CARRY",
            "oos_sharpe": 2.5,
            "oos_exp": 4.5,
            "oos_dd": 0.05,
            "annualized_return": 0.28,
            "annualized_vol": 0.08,
        },
        "TREND_ETH_SWING": {
            "horizon": "SWING",
            "oos_sharpe": 1.4,
            "oos_exp": 0.25,
            "oos_dd": 0.12,
            "annualized_return": 0.18,
            "annualized_vol": 0.22,
        },
        "BREAKOUT_SOL_INTRADAY": {
            "horizon": "INTRADAY",
            "oos_sharpe": 1.2,
            "oos_exp": 0.18,
            "oos_dd": 0.14,
            "annualized_return": 0.15,
            "annualized_vol": 0.25,
        },
        "MEANREV_ADA_INTRADAY": {
            "horizon": "INTRADAY",
            "oos_sharpe": 1.1,
            "oos_exp": 0.15,
            "oos_dd": 0.10,
            "annualized_return": 0.12,
            "annualized_vol": 0.20,
        },
        "DCA_BTC_INVEST": {
            "horizon": "INVEST",
            "oos_sharpe": 0.9,
            "oos_exp": 0.10,
            "oos_dd": 0.18,
            "annualized_return": 0.14,
            "annualized_vol": 0.30,
        },
    }


def test_portfolio_weights_enforce_concentration_cap(mock_strategy_stats):
    engine = PortfolioEngine(PortfolioConstraints(max_book_weight=0.20))
    weights = engine.compute_weights(mock_strategy_stats)

    # Even though CARRY_BTC has massive Sharpe (2.5) and high expectancy (4.5),
    # it must NEVER exceed the 20% cap!
    assert weights["CARRY_BTC"] <= 0.2001
    for k, w in weights.items():
        assert w <= 0.2001

    # Sum of weights must equal 1.0
    assert abs(sum(weights.values()) - 1.0) < 1e-3


def test_capital_allocation_sums_to_equity(mock_strategy_stats):
    engine = PortfolioEngine()
    allocations = engine.allocate_capital(mock_strategy_stats, total_equity=100_000.0)

    # Sum of allocations equals $100,000
    total_allocated = sum(allocations.values())
    assert abs(total_allocated - 100_000.0) < 1.0
    assert allocations["CARRY_BTC"] <= 20_001.0


def test_portfolio_metrics_and_diversification(mock_strategy_stats):
    engine = PortfolioEngine()
    weights = engine.compute_weights(mock_strategy_stats)
    metrics = engine.evaluate_metrics(weights, mock_strategy_stats)

    assert isinstance(metrics, PortfolioMetrics)
    assert metrics.expected_annual_return > 0.10
    assert metrics.annual_volatility > 0.05
    assert metrics.sharpe_ratio > 0.8
    assert metrics.allocated_books_count == 5
    # Herfindahl index for 5 equally capped books should be <= 0.25
    assert metrics.herfindahl_concentration <= 0.25


def test_portfolio_stress_testing(mock_strategy_stats):
    engine = PortfolioEngine()
    weights = engine.compute_weights(mock_strategy_stats)

    stress_result = engine.stress_test_portfolio(
        weights,
        mock_strategy_stats,
        funding_compression=0.50,
        vol_expansion_multiplier=1.50,
        correlated_shock_dd=0.15,
    )

    assert "baseline" in stress_result
    assert "stressed" in stress_result
    assert stress_result["survives_stress"] is True
    # Stressed return is lower than baseline
    assert stress_result["stressed"]["expected_return"] < stress_result["baseline"]["expected_return"]
    # Stressed volatility is higher than baseline
    assert stress_result["stressed"]["volatility"] > stress_result["baseline"]["volatility"]
