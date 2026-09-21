"""
Unit tests for QCP OpportunityMemory with Failure Taxonomy.
"""

import os
import tempfile
import pytest
from research.opportunity_memory import OpportunityMemory, FailureCategory


@pytest.fixture
def temp_memory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    mem = OpportunityMemory(db_path=db_path)
    yield mem
    if os.path.exists(db_path):
        os.remove(db_path)


def test_opportunity_memory_lifecycle(temp_memory):
    # Test recording falsification
    temp_memory.record_hypothesis_evaluation(
        alpha_id="HYP-OPP-VOLSQZ-SOLUSDT-0001",
        opportunity_type="DIRECTIONAL",
        symbol="SOL/USDT",
        timeframe="4h",
        falsified=True,
        failure_reason="Sub-threshold net edge (+0.088R) below paper gate hurdle (+0.20R)",
        net_edge_r=0.088
    )

    assert temp_memory.is_recently_falsified("DIRECTIONAL", "SOL/USDT")
    assert not temp_memory.is_recently_falsified("CARRY", "SOL/USDT")

    # Record surviving candidate
    temp_memory.record_hypothesis_evaluation(
        alpha_id="HYP-OPP-CARRY-SOLUSDT-0002",
        opportunity_type="CARRY",
        symbol="SOL/USDT",
        timeframe="4h",
        falsified=False,
        failure_reason="PASSED_AUDIT",
        net_edge_r=0.45
    )

    stats = temp_memory.get_memory_stats()
    assert stats["total_hypotheses_evaluated"] == 2
    assert stats["falsified_hypotheses"] == 1
    assert stats["survived_hypotheses"] == 1
    assert "SUB_HURDLE_EDGE" in stats["failure_taxonomy_distribution"]

    history = temp_memory.get_falsification_history()
    assert len(history) == 2


def test_opportunity_memory_reopening_conditions(temp_memory):
    # Record a failure under TRENDING_BULL regime
    temp_memory.record_hypothesis_evaluation(
        alpha_id="HYP-REV-BTCUSDT-001",
        opportunity_type="RELATIVE_VALUE",
        symbol="BTC/USDT",
        timeframe="1h",
        falsified=True,
        failure_reason="Friction overwhelmed edge in low-vol trending market",
        net_edge_r=-0.05,
        regime_context="TRENDING_BULL"
    )

    # In the same regime, reopening is suppressed
    can_reopen, reason = temp_memory.can_reopen_hypothesis(
        opportunity_type="RELATIVE_VALUE",
        symbol="BTC/USDT",
        current_regime="TRENDING_BULL",
        has_new_features=False
    )
    assert not can_reopen
    assert "Active memory suppression" in reason

    # In a different regime (e.g. HIGH_VOLATILITY_CHOP), reopening is justified
    can_reopen_regime, reason_regime = temp_memory.can_reopen_hypothesis(
        opportunity_type="RELATIVE_VALUE",
        symbol="BTC/USDT",
        current_regime="HIGH_VOLATILITY_CHOP",
        has_new_features=False
    )
    assert can_reopen_regime
    assert "Regime shifted" in reason_regime

    # With expanded feature set, reopening is justified
    can_reopen_feat, reason_feat = temp_memory.can_reopen_hypothesis(
        opportunity_type="RELATIVE_VALUE",
        symbol="BTC/USDT",
        current_regime="TRENDING_BULL",
        has_new_features=True
    )
    assert can_reopen_feat
    assert "Expanded feature space" in reason_feat
