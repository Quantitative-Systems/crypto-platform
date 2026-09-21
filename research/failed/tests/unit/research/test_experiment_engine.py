"""
Unit Tests for Research Experiment Engine & Schema
"""

import pytest
from research.experiments.experiment_schema import HypothesisSpec, ExperimentResult
from research.experiments.experiment_engine import ExperimentEngine


def test_hypothesis_spec_creation():
    spec = HypothesisSpec(
        hypothesis_id="HYP_TEST_001",
        hypothesis_name="Keyzone Invalidation Consumption",
        mechanism_description="Invalidate MTF keyzone after initial stop-out to prevent repeated entries",
        variable_under_test="zone_consumption_on_invalidation",
        falsification_criteria={"min_trades": 5, "min_expectancy_r": 0.0}
    )
    d = spec.to_dict()
    assert d["hypothesis_id"] == "HYP_TEST_001"
    assert d["variable_under_test"] == "zone_consumption_on_invalidation"
    assert "MAX_RISK_FRACTION_1_PCT" in d["control_invariants"]


def test_experiment_engine_metrics_aggregation():
    streams = [
        {
            "stream_id": "BTC_SET_4",
            "performance": {
                "total_trades": 1,
                "wins": 1,
                "losses": 0,
                "gross_realized_r": 0.27,
                "total_friction_r": 0.03,
                "net_realized_r": 0.24,
                "net_pnl_usd": 23.85,
                "max_drawdown_pct": 0.0
            }
        },
        {
            "stream_id": "SOL_SET_3",
            "performance": {
                "total_trades": 10,
                "wins": 2,
                "losses": 8,
                "gross_realized_r": -5.0,
                "total_friction_r": 0.3,
                "net_realized_r": -5.3,
                "net_pnl_usd": -500.0,
                "max_drawdown_pct": 5.2
            }
        }
    ]
    
    agg = ExperimentEngine.compute_aggregate_metrics(streams)
    assert agg["total_trades"] == 11
    assert agg["wins"] == 3
    assert agg["losses"] == 8
    assert agg["win_rate_pct"] == 27.27
    assert agg["sample_confidence"] == "PRELIMINARY_SAMPLE"


def test_experiment_engine_falsification_evaluation():
    spec = HypothesisSpec(
        hypothesis_id="HYP_FAIL",
        hypothesis_name="Failing Hypothesis",
        mechanism_description="Test failure",
        falsification_criteria={"min_trades": 10, "min_expectancy_r": 0.0, "require_better_net_r": True}
    )
    
    base_metrics = {"net_realized_r": -9.88}
    
    # Case 1: Degraded performance
    treat_metrics_worse = {"total_trades": 15, "net_realized_r": -12.5, "expectancy_r": -0.83}
    decision, reason = ExperimentEngine.evaluate_falsification(spec, base_metrics, treat_metrics_worse, [])
    assert decision == "REJECTED"
    
    # Case 2: Zero trades
    treat_metrics_zero = {"total_trades": 0, "net_realized_r": 0.0, "expectancy_r": None}
    decision, reason = ExperimentEngine.evaluate_falsification(spec, base_metrics, treat_metrics_zero, [])
    assert decision == "REJECTED"
    
    # Case 3: Improved but small sample
    treat_metrics_small = {"total_trades": 3, "net_realized_r": -1.0, "expectancy_r": -0.33}
    decision, reason = ExperimentEngine.evaluate_falsification(spec, base_metrics, treat_metrics_small, [])
    assert decision == "INCONCLUSIVE"
    
    # Case 4: Improved with sufficient sample
    treat_metrics_pass = {"total_trades": 12, "net_realized_r": 2.5, "expectancy_r": 0.208}
    decision, reason = ExperimentEngine.evaluate_falsification(spec, base_metrics, treat_metrics_pass, [])
    assert decision == "SURVIVES_FOR_OOS"
