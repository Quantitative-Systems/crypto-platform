"""
Integration tests for the QCP Empirical Alpha Discovery Pipeline.
Tests the autonomous end-to-end cycle:
Universe Certification -> Opportunity Formulation -> Autonomous Prioritization
-> Causal Backtesting (DEV/VAL/OOS) -> Adversarial Stress -> Rejection Taxonomy
-> Multiple Testing Control -> Canonical Report Generation.
"""

import json
from pathlib import Path
import pytest

from research.discovery_lab.empirical_alpha_discovery_engine import EmpiricalAlphaDiscoveryEngine


def test_alpha_discovery_pipeline_end_to_end():
    engine = EmpiricalAlphaDiscoveryEngine()
    result = engine.run_discovery_cycle()

    # 1. Structural schema assertions
    assert "discovery_timestamp_utc" in result
    assert "certified_universe_assets" in result
    assert "total_certified_datasets" in result
    assert result["total_certified_datasets"] >= 20
    assert "multiple_testing_registry" in result
    assert "evaluations_summary" in result
    assert "rejection_taxonomy_breakdown" in result
    assert "economic_truth_verdict" in result
    assert "governance" in result
    assert "evaluations_detail" in result
    assert "next_research_queue" in result

    # 2. Capital gate enforcement
    assert result["governance"]["live_capital_usd"] == 0.00
    assert result["governance"]["order_submission"] == "DISABLED"
    assert result["governance"]["capital_firewall"] == "FAIL_CLOSED"

    # 3. Multiple-testing tracking
    reg = result["multiple_testing_registry"]
    assert reg["total_hypotheses_evaluated"] >= 10
    assert reg["total_strategy_variants_tested"] >= 10
    assert reg["bonferroni_adjusted_hurdle_r"] >= 0.20

    # 4. Rejection and Falsification Accounting
    summary = result["evaluations_summary"]
    assert summary["total_candidates_evaluated"] >= 15
    assert summary["candidates_blocked_data"] >= 6
    assert summary["candidates_falsified"] >= 10

    # 5. Scientific truth verdict
    assert result["economic_truth_verdict"] == "NO_NEW_ECONOMIC_EDGE_VALIDATED"

    # 6. Artifact persistence verification
    json_path = Path(engine.output_dir) / "QCP_ALPHA_DISCOVERY_REPORT.json"
    md_path = Path(engine.output_dir) / "QCP_ALPHA_DISCOVERY_REPORT.md"
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, "r") as f:
        disk_data = json.load(f)
    assert disk_data["economic_truth_verdict"] == result["economic_truth_verdict"]
    assert disk_data["evaluations_summary"] == result["evaluations_summary"]

    with open(md_path, "r") as f:
        md_text = f.read()
    assert "NO_NEW_ECONOMIC_EDGE_VALIDATED" in md_text
    assert "$0.00 (LOCKED)" in md_text
    assert "Ranked Next Research Queue" in md_text
