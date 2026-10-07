"""
Unit tests for Canonical Multi-Year Matrix Runner.
"""

import os
import tempfile
import pytest
from research.experiments.hypothesis_registry import HypothesisRegistry
from research.experiments.run_canonical_multiyear_matrix import CanonicalMultiYearMatrixRunner


def test_canonical_multiyear_matrix_execution():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        reg_file = tf.name

    try:
        registry = HypothesisRegistry(registry_file=reg_file)
        runner = CanonicalMultiYearMatrixRunner(registry=registry)
        summary = runner.run_matrix()

        assert summary["hypothesis_id"] == "HTF_TREND_CONTINUATION_V1"
        assert summary["total_trades"] == 35
        assert summary["is_trades_count"] == 12
        assert summary["benchmark_trades_count"] == 12
        assert summary["oos_trades_count"] == 11
        assert "block_bootstrap" in summary
        assert "regime_decomposition" in summary
        assert "capital_barrier_tier" in summary
        assert summary["capital_barrier_tier"] in [
            "REJECTED_RESEARCH_ONLY",
            "RESEARCH_VALIDATED",
            "PAPER_ELIGIBLE",
            "MICRO_LIVE_ELIGIBLE",
            "PRODUCTION_ELIGIBLE"
        ]

        # Verify child hypotheses were registered
        assert "H1.1_SUPERSEDED_HTF_CONTEXT_RELAXED" in registry.hypotheses
        assert "H1.2_HTF_PERSISTENCE_MODEL" in registry.hypotheses
        assert registry.hypotheses["H1.1_SUPERSEDED_HTF_CONTEXT_RELAXED"].parent_hypothesis_id == "HTF_TREND_CONTINUATION_V1"
    finally:
        if os.path.exists(reg_file):
            os.remove(reg_file)
