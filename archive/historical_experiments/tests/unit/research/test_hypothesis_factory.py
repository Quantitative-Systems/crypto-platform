"""
Unit tests for HypothesisFactory and Multi-Model Stress Testing.
"""

import os
import tempfile
import pytest
from research.experiments.hypothesis_registry import HypothesisRegistry
from research.experiments.run_hypothesis_factory import HypothesisFactory


def test_hypothesis_factory_evaluation_and_registry_integration():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        reg_file = tf.name

    try:
        registry = HypothesisRegistry(registry_file=reg_file)
        factory = HypothesisFactory(registry=registry)

        results = factory.run_factory_evaluation()

        assert len(results) == 5  # H1 through H5
        # Verify that all tested models received a decision from the Capital Barrier
        for r in results:
            assert "capital_barrier_decision" in r
            assert r["capital_barrier_decision"] in ["APPROVED_FOR_DEPLOYMENT", "REJECTED_RESEARCH_ONLY"]
            assert "block_bootstrap_5th_pct_r" in r
            assert "cost_shocks" in r

        # Verify registry updated
        assert len(registry.hypotheses) == 5
        assert registry.trial_counter == 5
    finally:
        if os.path.exists(reg_file):
            os.remove(reg_file)
