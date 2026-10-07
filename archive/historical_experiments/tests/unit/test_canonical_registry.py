"""
Unit tests for Canonical Strategy Registry & Lifecycle Manager.
"""

import os
import pytest
from platform_core.canonical_strategy_registry import (
    CanonicalStrategyRegistry,
    StrategyLifecycleState,
)


def test_registry_registration_and_transitions(tmp_path):
    reg_file = str(tmp_path / "test_strategy_registry.json")
    registry = CanonicalStrategyRegistry(registry_file=reg_file)

    # Register candidate
    rec = registry.register_candidate(
        strategy_id="TEST-STRAT-001",
        version="v1.0.0",
        family_id="FAM-07",
        family_name="Multi-Timeframe Continuation",
        symbol="SOLUSDT",
        timeframe_set=3,
        trading_style="Swing / Intraday",
        hypothesis={"name": "test"},
        rules={"sl": "atr"},
        risk_model={"risk_pct": 0.006},
        initial_status=StrategyLifecycleState.RESEARCH,
    )
    assert rec["strategy_id"] == "TEST-STRAT-001"
    assert rec["status"] == StrategyLifecycleState.RESEARCH.value

    # Valid transition to DEVELOPMENT_PASS
    registry.transition_status(
        strategy_id="TEST-STRAT-001",
        new_status=StrategyLifecycleState.DEVELOPMENT_PASS,
        reason="Passed In-Sample Dev test",
    )
    c = registry.get_candidate("TEST-STRAT-001")
    assert c["status"] == StrategyLifecycleState.DEVELOPMENT_PASS.value
    assert len(c["status_history"]) == 2

    # Illegal transition: DEVELOPMENT_PASS -> LIVE directly should raise ValueError
    with pytest.raises(ValueError):
        registry.transition_status(
            strategy_id="TEST-STRAT-001",
            new_status=StrategyLifecycleState.LIVE,
            reason="Illegal leap",
            force=False,
        )

    # Pipeline summary test
    summary = registry.get_pipeline_summary()
    assert summary[StrategyLifecycleState.DEVELOPMENT_PASS.value] == 1
    assert summary[StrategyLifecycleState.RESEARCH.value] == 0
