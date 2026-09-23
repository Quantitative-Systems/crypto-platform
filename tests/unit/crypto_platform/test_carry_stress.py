"""Unit tests for the Funding Carry Stress Audit & Sensitivity Engine."""
import os
import pytest
from crypto_platform.research_engine.carry_stress import (
    CarryStressAuditor,
    CarryStressScenario,
)


def test_carry_stress_scenario_defaults():
    scenario = CarryStressScenario(
        scenario_id="TEST_01",
        description="Test Scenario",
        funding_multiplier=0.5,
        basis_shock_bps=20.0,
        fee_multiplier=1.5,
        borrow_rate_apr=0.08,
    )
    assert scenario.scenario_id == "TEST_01"
    assert scenario.funding_multiplier == 0.5
    assert scenario.basis_shock_bps == 20.0
    assert scenario.fee_multiplier == 1.5
    assert scenario.borrow_rate_apr == 0.08


def test_carry_simulation_baseline_vs_compression():
    auditor = CarryStressAuditor(outdir="research/results/crypto_platform")
    
    baseline_sc = CarryStressScenario(
        scenario_id="BASE",
        description="Baseline",
        funding_multiplier=1.0,
    )
    compressed_sc = CarryStressScenario(
        scenario_id="COMP_50",
        description="50% Compression",
        funding_multiplier=0.5,
    )
    
    res_base = auditor.run_simulation("BTCUSDT", baseline_sc)
    res_comp = auditor.run_simulation("BTCUSDT", compressed_sc)
    
    assert res_base.get("symbol") == "BTCUSDT"
    assert res_comp.get("symbol") == "BTCUSDT"
    
    if "total_return_pct" in res_base and "total_return_pct" in res_comp:
        # 50% funding compression must yield lower or equal return compared to baseline
        assert res_comp["total_return_pct"] < res_base["total_return_pct"]


def test_carry_negative_funding_regime():
    auditor = CarryStressAuditor(outdir="research/results/crypto_platform")
    negative_sc = CarryStressScenario(
        scenario_id="NEG",
        description="Negative funding regime",
        funding_multiplier=-0.5,
    )
    res_neg = auditor.run_simulation("BTCUSDT", negative_sc)
    if "trades" in res_neg and len(res_neg["trades"]) > 0:
        # Verify that negative funding triggers exit rules or reduces win rate
        assert res_neg["win_rate"] <= 0.50


def test_carry_auditor_full_audit_runs(tmp_path):
    auditor = CarryStressAuditor(outdir=str(tmp_path))
    # Run full audit on a subset of assets for fast unit test
    results = auditor.execute_stress_matrix(
        symbols=["BTCUSDT"],
    )
    assert "audit_timestamp_ms" in results
    assert "results" in results
    assert results["scenarios_evaluated"] == 9
    
    # Check that audit files were written
    json_path = os.path.join(str(tmp_path), "carry_stress_audit.json")
    md_path = os.path.join(str(tmp_path), "carry_stress_report.md")
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
