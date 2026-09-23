"""Unit tests for the Strategy Discovery Engine and promotion invariant."""
import json
import os
import pytest
from crypto_platform.core.domain import OperatingMode
from crypto_platform.discovery.discovery_loop import StrategyDiscoveryEngine


def test_discovery_engine_initialization(tmp_path):
    results_dir = os.path.join(str(tmp_path), "results")
    failed_dir = os.path.join(str(tmp_path), "failed")
    engine = StrategyDiscoveryEngine(results_dir=results_dir, failed_archive_dir=failed_dir)
    assert os.path.exists(results_dir)
    assert os.path.exists(failed_dir)


def test_discovery_campaign_paper_only_invariant(tmp_path):
    results_dir = os.path.join(str(tmp_path), "results")
    failed_dir = os.path.join(str(tmp_path), "failed")
    engine = StrategyDiscoveryEngine(results_dir=results_dir, failed_archive_dir=failed_dir)

    # Run quick sweep on single horizon and asset
    summary = engine.run_discovery_campaign(
        horizons=["SWING"],
        symbols=["BTCUSDT"],
        verbose=False,
    )

    assert "target_environment" in summary
    # INVARIANT: Must strictly be PAPER, never LIVE
    assert summary["target_environment"] == OperatingMode.PAPER.value

    # Verify failed archive exists
    assert os.path.exists(summary["failed_archive_path"])
    with open(summary["failed_archive_path"]) as f:
        failed_data = json.load(f)
        assert "candidates" in failed_data

    # Verify promoted manifest exists
    assert os.path.exists(summary["evidence_manifest_path"])
    with open(summary["evidence_manifest_path"]) as f:
        promoted_data = json.load(f)
        assert promoted_data["target_environment"] == OperatingMode.PAPER.value
