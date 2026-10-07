"""
Unit tests for Regime Decomposition and Parameter Cliff Detector.
"""

import pytest
from research.analytics.statistical_validator import StatisticalValidator


def test_regime_decomposition_grouping():
    trades = [
        {"net_r": 4.0, "trend_regime": "BULL_TREND", "volatility_regime": "HIGH_VOLATILITY", "market_phase": "CONTINUATION"},
        {"net_r": -1.0, "trend_regime": "BULL_TREND", "volatility_regime": "HIGH_VOLATILITY", "market_phase": "CONTINUATION"},
        {"net_r": -1.0, "trend_regime": "RANGE_CHOP", "volatility_regime": "COMPRESSION", "market_phase": "PULLBACK"},
        {"net_r": -1.0, "trend_regime": "RANGE_CHOP", "volatility_regime": "COMPRESSION", "market_phase": "PULLBACK"},
    ]

    report = StatisticalValidator.decompose_by_regime(trades)

    assert "BULL_TREND" in report
    assert "RANGE_CHOP" in report
    assert report["BULL_TREND"]["trades"] == 2
    assert report["BULL_TREND"]["mean_expectancy_r"] == 1.50
    assert report["RANGE_CHOP"]["trades"] == 2
    assert report["RANGE_CHOP"]["mean_expectancy_r"] == -1.00


def test_parameter_cliff_stability_detection():
    # Stable plateau: drops within 15%
    stable = StatisticalValidator.test_parameter_cliff_stability(
        baseline_exp_r=0.40,
        perturbed_expectancies={"minus_10_pct": 0.38, "plus_10_pct": 0.36},
        max_allowed_drop_pct=0.30
    )
    assert stable["is_stable"] is True
    assert stable["verdict"] == "STABLE_PARAMETER_PLATEAU"

    # Fragile cliff: drops from +0.40R to -0.05R (112.5% drop)
    cliff = StatisticalValidator.test_parameter_cliff_stability(
        baseline_exp_r=0.40,
        perturbed_expectancies={"minus_10_pct": -0.05, "plus_10_pct": 0.35},
        max_allowed_drop_pct=0.30
    )
    assert cliff["is_stable"] is False
    assert cliff["verdict"] == "FRAGILE_PARAMETER_CLIFF"
