"""
Unit tests for Continuous Evolution Engine.
"""

import pytest
from research.discovery_lab.continuous_evolution_engine import (
    ContinuousEvolutionEngine,
    DiagnosisCategory,
)
from risk_engine.risk_coordinator_v2 import DegradationStatus
from platform_core.canonical_strategy_registry import (
    CanonicalStrategyRegistry,
    StrategyLifecycleState,
)


def test_continuous_evolution_nominal_telemetry(tmp_path):
    reg_file = str(tmp_path / "test_evo_registry.json")
    registry = CanonicalStrategyRegistry(registry_file=reg_file)
    registry.register_candidate(
        strategy_id="TEST-STRAT-EVO",
        version="v1.0.0",
        family_id="FAM-07",
        family_name="MTF Continuation",
        symbol="SOLUSDT",
        timeframe_set=3,
        trading_style="Intraday",
        hypothesis={"name": "test"},
        rules={},
        risk_model={"risk_pct": 0.006},
        initial_status=StrategyLifecycleState.QUALIFIED_ROBUST,
        development_results={"max_drawdown_r": 15.0, "win_rate": 45.0, "expectancy_r": 0.20},
    )

    engine = ContinuousEvolutionEngine(registry=registry)

    # 10 nominal forward trades with 5 wins and 5 losses (no large DD)
    nominal_trades = [
        {"pnl_r": 2.0}, {"pnl_r": -1.0}, {"pnl_r": 1.5}, {"pnl_r": -1.0},
        {"pnl_r": 2.5}, {"pnl_r": -1.0}, {"pnl_r": 1.0}, {"pnl_r": -1.0},
        {"pnl_r": 3.0}, {"pnl_r": -1.0},
    ]
    report = engine.evaluate_strategy_telemetry(
        strategy_id="TEST-STRAT-EVO",
        forward_telemetry_trades=nominal_trades,
    )
    assert report.degradation_status == DegradationStatus.NOMINAL
    assert report.diagnosis == DiagnosisCategory.NOMINAL_VARIANCE
    assert report.recommended_hypothesis_ticket is None


def test_continuous_evolution_quarantine_trigger(tmp_path):
    reg_file = str(tmp_path / "test_evo_registry.json")
    registry = CanonicalStrategyRegistry(registry_file=reg_file)
    registry.register_candidate(
        strategy_id="TEST-STRAT-EVO",
        version="v1.0.0",
        family_id="FAM-07",
        family_name="MTF Continuation",
        symbol="SOLUSDT",
        timeframe_set=3,
        trading_style="Intraday",
        hypothesis={"name": "test"},
        rules={},
        risk_model={"risk_pct": 0.006},
        initial_status=StrategyLifecycleState.QUALIFIED_ROBUST,
        development_results={"max_drawdown_r": 10.0, "win_rate": 45.0, "expectancy_r": 0.20},
    )

    engine = ContinuousEvolutionEngine(registry=registry)

    # 20 consecutive losses (20R drawdown, which is 2.0x historical max DD of 10R)
    disaster_trades = [{"pnl_r": -1.0} for _ in range(20)]
    report = engine.evaluate_strategy_telemetry(
        strategy_id="TEST-STRAT-EVO",
        forward_telemetry_trades=disaster_trades,
    )
    assert report.degradation_status == DegradationStatus.QUARANTINED
    assert report.diagnosis == DiagnosisCategory.STRUCTURAL_ALPHA_DECAY
    assert report.recommended_hypothesis_ticket is not None
    assert "Quarantine" in report.diagnostic_details

    # Check that Canonical Registry status was transitioned to QUARANTINED
    cand = registry.get_candidate("TEST-STRAT-EVO")
    assert cand["status"] == StrategyLifecycleState.QUARANTINED.value
