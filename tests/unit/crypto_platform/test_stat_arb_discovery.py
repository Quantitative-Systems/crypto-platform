"""Unit tests for Statistical Arbitrage Discovery engine."""
import os
import pytest
from crypto_platform.discovery.statistical_arbitrage_discovery import (
    StatisticalArbitrageDiscovery,
    StatArbCandidate,
)


def test_stat_arb_candidate_insufficient_data(tmp_path):
    results_dir = str(tmp_path / "results")
    failed_dir = str(tmp_path / "failed")
    disc = StatisticalArbitrageDiscovery(results_dir=results_dir, failed_dir=failed_dir)

    # Candidate with non-existent symbol
    cand = StatArbCandidate("FAKE_PAIR", "NONEXISTENT_A", "NONEXISTENT_B")
    res = disc.evaluate_pair(cand)

    assert "FAILED" in res["verdict"]
    assert os.path.exists(os.path.join(failed_dir, "FAILED_arb_FAKE_PAIR.json"))


def test_stat_arb_discovery_campaign_runs(tmp_path):
    results_dir = str(tmp_path / "results")
    failed_dir = str(tmp_path / "failed")
    disc = StatisticalArbitrageDiscovery(results_dir=results_dir, failed_dir=failed_dir)

    summary = disc.run_discovery_campaign()
    assert "total_candidates" in summary
    assert summary["total_candidates"] == 4
    assert os.path.exists(os.path.join(results_dir, "stat_arb_discovery_summary.json"))
