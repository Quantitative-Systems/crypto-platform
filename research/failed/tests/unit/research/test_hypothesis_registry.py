"""
Unit tests for HypothesisRegistry and Multiple Hypothesis Testing tracking.
"""

import os
import tempfile
import pytest
from research.experiments.hypothesis_registry import (
    HypothesisRegistry,
    HypothesisFamily,
    HypothesisLifecycleState
)


def test_hypothesis_registry_lifecycle_and_provenance():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        reg_file = tf.name

    try:
        registry = HypothesisRegistry(registry_file=reg_file)
        
        # Register new hypothesis
        h = registry.register_hypothesis(
            hypothesis_id="TEST_H1_TREND",
            hypothesis_name="Test Trend Continuation",
            family=HypothesisFamily.H1_TREND_CONTINUATION,
            description="Unit test model",
            parameters={"min_rr": 4.0}
        )

        assert h.hypothesis_id == "TEST_H1_TREND"
        assert h.lifecycle_state == HypothesisLifecycleState.CANDIDATE
        assert h.trial_index == 1
        assert registry.get_multiple_testing_penalty() == 1.0

        # Register second hypothesis
        h2 = registry.register_hypothesis(
            hypothesis_id="TEST_H2_VOLATILITY",
            hypothesis_name="Test Volatility Model",
            family=HypothesisFamily.H2_VOLATILITY_EXPANSION,
            description="Unit test model 2",
            parameters={"atr_mult": 1.2}
        )
        assert h2.trial_index == 2
        assert registry.get_multiple_testing_penalty() == 2.0

        # Record empirical falsification
        registry.record_falsification(
            hypothesis_id="TEST_H1_TREND",
            reason="Negative expectancy -0.25R",
            benchmark_metrics={"expectancy_r": -0.25}
        )

        assert registry.hypotheses["TEST_H1_TREND"].lifecycle_state == HypothesisLifecycleState.REJECTED_EMPIRICALLY
        assert registry.hypotheses["TEST_H1_TREND"].rejection_reason == "Negative expectancy -0.25R"

        # Reload from disk to verify persistence
        registry2 = HypothesisRegistry(registry_file=reg_file)
        assert len(registry2.hypotheses) == 2
        assert registry2.trial_counter == 2
        assert registry2.hypotheses["TEST_H1_TREND"].lifecycle_state == HypothesisLifecycleState.REJECTED_EMPIRICALLY
    finally:
        if os.path.exists(reg_file):
            os.remove(reg_file)
