"""
Integration test for Autonomous Platform Orchestrator full cycle execution.
"""

from pathlib import Path
from production.autonomous_platform_orchestrator import AutonomousPlatformOrchestrator


def test_autonomous_platform_orchestrator_full_cycle(tmp_path):
    orchestrator = AutonomousPlatformOrchestrator(output_dir=tmp_path)
    summary = orchestrator.execute_full_cycle()

    assert summary is not None
    assert "data_fabric" in summary
    assert "market_regime" in summary
    assert "research_factory" in summary
    assert "falsification_audit" in summary
    assert "execution_capacity" in summary
    assert "exposure_graph" in summary
    assert "portfolio_allocation" in summary
    assert "risk_governor_decisions" in summary
    assert "stress_lab_report" in summary
    assert "economic_truth_attribution" in summary
    assert summary["governance"]["live_capital_usd"] == 0.00
    assert summary["governance"]["capital_firewall"] == "FAIL_CLOSED"

    # Verify output artifacts exist
    assert (tmp_path / "QCP_INSTITUTIONAL_CAPABILITY_AUDIT.json").exists()
    assert (tmp_path / "QCP_MASTER_ECONOMIC_STATE.md").exists()
    assert (tmp_path / "ALPHA_EXPOSURE_GRAPH.json").exists()
    assert (tmp_path / "STRESS_SHOCK_REPORT.json").exists()
    assert (tmp_path / "QCP_PRODUCTION_READINESS_AUDIT.json").exists()
    assert (tmp_path / "QCP_PRODUCTION_READINESS_AUDIT.md").exists()
    assert (tmp_path / "QCP_AUTONOMOUS_RESEARCH_AUDIT.json").exists()
    assert (tmp_path / "QCP_DATA_LINEAGE_AUDIT.json").exists()
    assert (tmp_path / "QCP_ALPHA_LIFECYCLE_STATE.json").exists()
    assert (tmp_path / "QCP_CAPABILITY_REGISTRY.json").exists()
