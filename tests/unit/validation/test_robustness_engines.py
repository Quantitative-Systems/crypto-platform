"""Unit tests for Monte Carlo Simulator and Parameter Stability Analyzer."""
import pytest

from validation.robustness import MonteCarloSimulator, ParameterStabilityAnalyzer


def test_monte_carlo_simulator_resilient_series():
    sim = MonteCarloSimulator(seed=42)
    # A resilient positive expectancy series (+4R, -1R, +4R, -1R, -1R, +4R)
    trades = [4.0, -1.0, 4.0, -1.0, -1.0, 4.0, -1.0, 4.0, -1.0, -1.0, 4.0, -1.0]
    report = sim.evaluate_candidate(trades, n_shuffles=200)

    assert report.original_trade_count == 12
    assert report.original_total_r > 0
    assert report.dropout_positive_expectancy_rate > 0.80
    assert report.p95_max_dd_r < 25.0
    assert report.is_monte_carlo_pass is True


def test_monte_carlo_simulator_failing_series():
    sim = MonteCarloSimulator(seed=42)
    # Negative expectancy series
    trades = [-1.0, -1.0, -1.0, -1.0, 0.5, -1.0, -1.0, -1.0]
    report = sim.evaluate_candidate(trades, n_shuffles=100)

    assert report.is_monte_carlo_pass is False


def test_parameter_stability_plateau():
    analyzer = ParameterStabilityAnalyzer()
    # Broad resilient plateau around param=20
    params = [10.0, 15.0, 20.0, 25.0, 30.0]
    expectancies = [0.45, 0.55, 0.60, 0.54, 0.48]

    report = analyzer.evaluate_1d_stability("lookback", params, expectancies)
    assert report.optimal_parameter_value == 20.0
    assert report.optimal_expectancy_r == 0.60
    assert report.plateau_stability_index >= 0.65
    assert report.is_stable_plateau is True


def test_parameter_stability_isolated_spike():
    analyzer = ParameterStabilityAnalyzer()
    # Sharp single-point spike at 20 that collapses to negative
    params = [10.0, 15.0, 20.0, 25.0, 30.0]
    expectancies = [-0.20, -0.10, 1.20, -0.30, -0.40]

    report = analyzer.evaluate_1d_stability("lookback", params, expectancies)
    assert report.optimal_parameter_value == 20.0
    assert report.is_stable_plateau is False
