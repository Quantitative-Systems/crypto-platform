"""
Unit tests for the Profitability Research Mandate pipeline:
- Research Integrity Audit (Phase 0)
- Forensic Failure Analysis (Phase 1)
- Hypothesis Registry (Phase 2)
- Scorecard Generator (Phase 3 & 7)
- Capital Barrier Governance (Phase 8)
"""

import os
import json
import pytest
from pathlib import Path

ROOT_DIR = Path("/home/mrcn2/crypto-platform")

from platform_core.capital_barrier import CapitalBarrier, CapitalBarrierTier
from research.hypotheses.hypothesis_registry import HypothesisRegistry, HypothesisRecord
from research.analytics.research_scorecard_generator import evaluate_hypothesis_on_development


def test_phase0_research_integrity_audit_passed():
    """Verifies that the 15-point Research Integrity Audit passed unconditionally with 0 violations."""
    audit_json = ROOT_DIR / "scratch/research_integrity_audit_results.json"
    assert audit_json.exists(), "scratch/research_integrity_audit_results.json must exist"
    
    with open(audit_json, "r") as f:
        data = json.load(f)
        
    meta = data.get("metadata", {})
    assert meta.get("master_verdict") == "AUDIT PASSED"
    assert meta.get("total_audit_points") == 15
    assert meta.get("passed_points") == 15
    assert meta.get("failed_points") == 0

    points = data.get("audit_points", {})
    assert len(points) == 15
    for p_name, p_res in points.items():
        assert p_res.get("status") == "PASS", f"Audit point {p_name} failed: {p_res}"


def test_phase1_forensic_failure_attribution():
    """Verifies that all 18 mandated failure categories are quantitatively analyzed."""
    forensic_json = ROOT_DIR / "scratch/forensic_failure_analysis.json"
    assert forensic_json.exists(), "scratch/forensic_failure_analysis.json must exist"

    with open(forensic_json, "r") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    assert meta.get("categories_evaluated") == 18
    assert "h1_forensic_analysis" in data
    assert "dev_forensic_analysis" in data
    assert "causal_rationales" in data

    h1_cats = data["h1_forensic_analysis"]
    assert len(h1_cats) == 18
    
    # Check that each category contains computed metrics
    for cat_name, buckets in h1_cats.items():
        assert len(buckets) > 0, f"Category {cat_name} has no sub-buckets"
        for b_name, b_metrics in buckets.items():
            assert "expectancy_r" in b_metrics
            assert "ci_95_bootstrap" in b_metrics
            assert "profit_factor" in b_metrics
            assert "avg_mfe_r" in b_metrics
            assert "avg_mae_r" in b_metrics


def test_phase2_hypothesis_registry_integrity():
    """Verifies that the hypothesis registry contains single-variable modifications and pre-registered parameters."""
    reg = HypothesisRegistry()
    assert len(reg.hypotheses) >= 8
    assert "HTF_TREND_CONTINUATION_V1" in reg.hypotheses
    assert "H1.1_EARLIER_MTF_ENTRY" in reg.hypotheses
    assert "H1.5_HTF_KEYZONE_FRESHNESS_7D" in reg.hypotheses

    for hid, h in reg.hypotheses.items():
        assert h.parent_hypothesis is not None
        assert len(h.exact_economic_rationale) > 20
        assert len(h.one_structural_modification) > 5
        assert isinstance(h.pre_registered_parameter, dict)
        assert len(h.pre_registered_parameter) > 0
        assert "period" in h.development_dataset
        assert "period" in h.validation_dataset
        assert "period" in h.untouched_oos_dataset


def test_phase7_scorecard_schema_and_rejection():
    """Verifies that scorecard generation produces valid machine-readable schema and correct rejection."""
    scorecard = evaluate_hypothesis_on_development("HTF_TREND_CONTINUATION_V1")
    
    assert scorecard["hypothesis_id"] == "HTF_TREND_CONTINUATION_V1"
    assert "financial_metrics" in scorecard
    assert "statistical_validation" in scorecard
    assert "cost_stress_testing" in scorecard
    assert "governance" in scorecard
    
    # Negative control must be rejected
    assert scorecard["governance"]["promotion_status"] == CapitalBarrierTier.REJECTED_RESEARCH_ONLY.value
    assert len(scorecard["governance"]["rejection_reasons"]) > 0


def test_phase8_capital_barrier_defense():
    """Verifies that negative expectancy strategies are blocked from capital allocation."""
    eval_result = CapitalBarrier.evaluate_deployment_eligibility(
        hypothesis_id="NEGATIVE_TEST",
        total_trades=50,
        net_expectancy_r=-0.50,
        bootstrap_lower_ci_r=-0.70,
        walk_forward_ratio=None,
        max_drawdown_pct=30.0,
        cost_shock_expectancy_r=-0.60
    )
    assert eval_result.decision == CapitalBarrierTier.REJECTED_RESEARCH_ONLY
    assert not eval_result.passed_all_gates
