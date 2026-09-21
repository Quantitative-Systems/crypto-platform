"""
Unit tests for CapitalBarrier and 3-Plane deployment gating.
"""

import pytest
from platform_core.capital_barrier import (
    CapitalBarrier,
    CapitalBarrierDecision,
    CapitalBarrierBreachError,
    CapitalBarrierEvaluation
)


def test_capital_barrier_rejects_negative_expectancy():
    # Strategy with negative expectancy (-0.24R)
    eval_result = CapitalBarrier.evaluate_deployment_eligibility(
        hypothesis_id="HTF_TREND_CONTINUATION_V1",
        total_trades=50,
        net_expectancy_r=-0.2376,
        bootstrap_lower_ci_r=-0.45,
        walk_forward_ratio=0.50,
        max_drawdown_pct=15.0,
        cost_shock_expectancy_r=-0.35
    )

    assert eval_result.passed_all_gates is False
    assert eval_result.decision == CapitalBarrierDecision.REJECTED_RESEARCH_ONLY
    assert any("ALPHA_EXPECTANCY" in r for r in eval_result.rejection_reasons)


def test_capital_barrier_rejects_insufficient_sample():
    # Strategy with positive expectancy but only N=10 trades
    eval_result = CapitalBarrier.evaluate_deployment_eligibility(
        hypothesis_id="TINY_SAMPLE_MODEL",
        total_trades=10,
        net_expectancy_r=0.45,
        bootstrap_lower_ci_r=0.10,
        walk_forward_ratio=0.85,
        max_drawdown_pct=5.0,
        cost_shock_expectancy_r=0.40
    )

    assert eval_result.passed_all_gates is False
    assert eval_result.decision == CapitalBarrierDecision.REJECTED_RESEARCH_ONLY
    assert any("STATISTICAL_SAMPLE" in r for r in eval_result.rejection_reasons)


def test_capital_barrier_approves_robust_model():
    # Institutional model passing all 6 gates
    eval_result = CapitalBarrier.evaluate_deployment_eligibility(
        hypothesis_id="VALIDATED_ROBUST_ALPHA",
        total_trades=120,
        net_expectancy_r=0.35,
        bootstrap_lower_ci_r=0.15,
        walk_forward_ratio=0.82,
        max_drawdown_pct=12.5,
        cost_shock_expectancy_r=0.28
    )

    assert eval_result.passed_all_gates is True
    assert eval_result.decision == CapitalBarrierDecision.PRODUCTION_ELIGIBLE
    assert len(eval_result.rejection_reasons) == 0


def test_capital_barrier_raises_breach_on_unapproved_live_deployment():
    eval_result = CapitalBarrier.evaluate_deployment_eligibility(
        hypothesis_id="UNVALIDATED_MODEL",
        total_trades=15,
        net_expectancy_r=-0.10,
        bootstrap_lower_ci_r=-0.30,
        walk_forward_ratio=0.20,
        max_drawdown_pct=25.0,
        cost_shock_expectancy_r=-0.20
    )

    with pytest.raises(CapitalBarrierBreachError) as exc_info:
        CapitalBarrier.enforce_barrier(eval_result, allow_research_sandbox=False)

    assert "CAPITAL BARRIER BREACH" in str(exc_info.value)
