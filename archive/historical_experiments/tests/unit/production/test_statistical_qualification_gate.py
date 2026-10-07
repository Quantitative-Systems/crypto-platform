"""
Tests for Statistical Qualification Gatekeeper.
Verifies the 3-tier lifecycle, bootstrap CI computation, premature promotion blocking,
and capital firewall enforcement.
"""

import pytest
import numpy as np
from production.qualification.statistical_qualification_gate import (
    StatisticalQualificationGatekeeper,
    QualificationHurdles,
    StrategyLifecycleTier,
)


def test_bootstrap_ci_calculation():
    gatekeeper = StatisticalQualificationGatekeeper()
    # 50 trades with positive mean
    trades = [1.0, 2.0, -1.0, 1.5, 0.5, -1.0, 2.0, 1.0, -1.0, 1.5] * 5
    res = gatekeeper.calculate_bootstrap_ci(trades, n_bootstrap=1000, alpha_pct=5.0)
    assert res.bootstrap_samples == 1000
    assert res.confidence_level_pct == 95.0
    assert res.ci_lower_bound_r <= res.mean_expectancy_r <= res.ci_upper_bound_r
    assert res.ci_lower_bound_r > 0.0


def test_premature_promotion_blocked():
    """
    Verifies that a strategy with only 15 trades and 14 days cannot be promoted to
    PRODUCTION_QUALIFIED, even if it has high win rate. Real capital remains locked.
    """
    gatekeeper = StatisticalQualificationGatekeeper(
        hurdles=QualificationHurdles(min_forward_trades=100, min_forward_days=60.0)
    )
    trades = [1.5, 2.0, 1.0, -1.0, 2.0, 1.5, 1.8, -1.0, 2.2, 1.5, 1.0, 2.0, -1.0, 1.5, 2.0]
    verdict = gatekeeper.evaluate_strategy(
        strategy_id="SOL_EARLY",
        symbol="SOL/USDT",
        historical_trades_count=365,
        forward_r_returns=trades,
        forward_elapsed_days=14.0,
        forward_max_drawdown_pct=2.0,
        forward_consecutive_losses=1,
        observed_friction_error_bps=1.0,
    )

    assert verdict.current_tier == StrategyLifecycleTier.FORWARD_HEALTHY
    assert verdict.is_production_qualified is False
    assert verdict.is_capital_firewall_locked is True
    assert verdict.live_execution_permitted is False
    assert verdict.gate_checks["gate_01_min_forward_trades"] is False
    assert verdict.gate_checks["gate_02_min_forward_days"] is False


def test_drawdown_exceeded_triggers_degradation():
    """
    Verifies that forward drawdown exceeding 1.25x historical ceiling (5.91%) triggers
    DEGRADED_OR_DISQUALIFIED.
    """
    gatekeeper = StatisticalQualificationGatekeeper()
    verdict = gatekeeper.evaluate_strategy(
        strategy_id="SOL_HIGH_DD",
        symbol="SOL/USDT",
        historical_trades_count=365,
        forward_r_returns=[-1.0] * 7,
        forward_elapsed_days=10.0,
        forward_max_drawdown_pct=6.5,  # Exceeds 5.91%
        forward_consecutive_losses=7,
        observed_friction_error_bps=1.0,
    )

    assert verdict.current_tier == StrategyLifecycleTier.DEGRADED_OR_DISQUALIFIED
    assert verdict.is_production_qualified is False
    assert verdict.is_capital_firewall_locked is True


def test_full_production_qualification():
    """
    Verifies that when all hurdles (100+ trades, 60+ days, bootstrap CI > +0.15R,
    low DD, low friction) are met, the strategy transitions to PRODUCTION_QUALIFIED.
    """
    gatekeeper = StatisticalQualificationGatekeeper(
        hurdles=QualificationHurdles(min_forward_trades=100, min_forward_days=60.0)
    )
    # 120 profitable trades with high expectancy
    rng = np.random.default_rng(42)
    trades = [float(rng.uniform(0.5, 2.5)) if rng.random() < 0.70 else -1.0 for _ in range(120)]
    verdict = gatekeeper.evaluate_strategy(
        strategy_id="FULLY_QUALIFIED_BENCHMARK",
        symbol="SOL/USDT",
        historical_trades_count=365,
        forward_r_returns=trades,
        forward_elapsed_days=65.0,
        forward_max_drawdown_pct=3.5,
        forward_consecutive_losses=2,
        observed_friction_error_bps=1.2,
    )

    assert verdict.current_tier == StrategyLifecycleTier.PRODUCTION_QUALIFIED
    assert verdict.is_production_qualified is True
    assert verdict.is_capital_firewall_locked is False
    assert verdict.live_execution_permitted is True
    assert all(verdict.gate_checks.values())
