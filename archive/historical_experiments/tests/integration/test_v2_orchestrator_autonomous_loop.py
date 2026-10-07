"""
Integration tests for QCP Autonomous Platform Orchestrator (v2).
Validates end-to-end autonomous discovery, data governance, research prioritization,
falsification, risk governance, hedging, stress testing, and truth attribution.
"""

import tempfile
import pytest
from pathlib import Path
from production.autonomous_platform_orchestrator import AutonomousPlatformOrchestrator


def test_v2_orchestrator_full_autonomous_cycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir)
        orchestrator = AutonomousPlatformOrchestrator(output_dir=out_path)

        summary = orchestrator.execute_full_cycle()

        # 1. Verify Structure & Subsystem outputs
        assert summary["orchestrator"] == "QCP Autonomous Platform Orchestrator (v2)"
        assert "data_fabric" in summary
        assert "market_regime" in summary
        assert "discovery" in summary
        assert "research_factory" in summary
        assert "falsification_audit" in summary
        assert "execution_capacity" in summary
        assert "exposure_graph" in summary
        assert "portfolio_allocation" in summary
        assert "hedging_decision" in summary
        assert "risk_governor_decisions" in summary
        assert "stress_lab_report" in summary
        assert "economic_truth_attribution" in summary

        # 2. Verify Capital Safety & Invariants
        assert summary["governance"]["live_capital_usd"] == 0.00
        assert summary["governance"]["live_order_submission"] == "DISABLED"
        assert summary["governance"]["capital_firewall"] == "FAIL_CLOSED"

        # 3. Verify Artifact Persistence
        audit_file = out_path / "QCP_INSTITUTIONAL_CAPABILITY_AUDIT.json"
        md_file = out_path / "QCP_MASTER_ECONOMIC_STATE.md"
        assert audit_file.exists()
        assert md_file.exists()
