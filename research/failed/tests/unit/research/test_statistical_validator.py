"""
Unit tests for StatisticalValidator.
"""

import pytest
from research.analytics.statistical_validator import (
    StatisticalValidator,
    StatisticalConfidenceReport
)


def test_compute_standard_error_basic():
    # 5 trades: [1.0, 1.0, 1.0, 1.0, 1.0] -> mean=1.0, std=0.0
    res = StatisticalValidator.compute_standard_error([1.0, 1.0, 1.0, 1.0, 1.0])
    assert res["mean"] == 1.0
    assert res["std_dev"] == 0.0
    assert res["std_error"] == 0.0
    assert res["ci_95_lower"] == 1.0
    assert res["ci_95_upper"] == 1.0


def test_bootstrap_resample_deterministic_seed():
    trades = [2.0, 3.0, 2.5, 4.0, 1.5]
    res = StatisticalValidator.bootstrap_resample(trades, n_resamples=500, seed=42)
    assert res["resamples"] == 500
    assert res["prob_positive_edge_pct"] == 100.0
    assert res["median_expectancy"] > 2.0
    assert res["pct_5th"] > 0.0


def test_block_bootstrap_resample():
    trades = [1.0, 4.0, -1.0, -1.0, 4.0, -1.0, 4.0, -1.0, -1.0, 1.0]
    res = StatisticalValidator.block_bootstrap_resample(trades, block_size=3, n_resamples=500, seed=42)
    assert res["resamples"] == 500
    assert res["block_size"] == 3
    assert res["mean_of_means"] > 0.0
    assert "pct_5th" in res
    assert "pct_95th" in res


def test_multiple_testing_penalty():
    # Raw p=0.02 with K=5 trials -> Bonferroni adjusted p = 0.10 (fails significance)
    res = StatisticalValidator.apply_multiple_testing_penalty(raw_p_value=0.02, trial_count=5)
    assert res["bonferroni_adjusted_p"] == pytest.approx(0.10)
    assert res["is_significant_at_5pct"] is False

    # Raw p=0.001 with K=5 trials -> Bonferroni adjusted p = 0.005 (survives significance)
    res2 = StatisticalValidator.apply_multiple_testing_penalty(raw_p_value=0.001, trial_count=5)
    assert res2["bonferroni_adjusted_p"] == pytest.approx(0.005)
    assert res2["is_significant_at_5pct"] is True


def test_evaluate_statistical_confidence_insufficient_sample():
    # N=10 trades (< 30)
    trades = [1.0] * 10
    report = StatisticalValidator.evaluate_statistical_confidence(trades, min_sample_size=30)
    assert report.is_statistically_significant is False
    assert "INSUFFICIENT_SAMPLE" in report.verdict
