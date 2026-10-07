"""
Integration tests for QCP Cross-Asset Uniformity Audit.

Verifies:
1. Artifact integrity of CROSS_ASSET_UNIFORMITY_AUDIT.json.
2. 100% directional concordance during simultaneous breakout signals.
3. Verdict of Case A (one replicated volatility regime exposure).
4. Validation of the downside correlation active-only vs naive distinction.
"""

import os
import json
import pytest

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "research", "results")
AUDIT_JSON_PATH = os.path.join(RESULTS_DIR, "CROSS_ASSET_UNIFORMITY_AUDIT.json")


@pytest.fixture
def cross_asset_data():
    if not os.path.exists(AUDIT_JSON_PATH):
        pytest.skip(f"Cross-asset audit file not found at {AUDIT_JSON_PATH}")
    with open(AUDIT_JSON_PATH, "r") as f:
        return json.load(f)


def test_cross_asset_schema_and_verdict(cross_asset_data):
    """Verifies that the verdict is Case A: Common Regime Replication."""
    assert "audit_name" in cross_asset_data
    assert cross_asset_data["audit_name"] == "CROSS_ASSET_UNIFORMITY_AUDIT"
    assert "verdict" in cross_asset_data
    assert cross_asset_data["verdict"] == "CASE_A_COMMON_REGIME_REPLICATION"


def test_directional_concordance_is_total(cross_asset_data):
    """
    Asserts that whenever BTC, ETH, and SOL trigger simultaneous breakout signals,
    directional concordance is 100% (zero opposing/hedging signals).
    """
    sig = cross_asset_data["signal_concurrency"]
    assert sig["simultaneous_btc_eth"] > 0
    assert sig["directional_concordance_btc_eth_pct"] == 100.0

    assert sig["simultaneous_btc_sol"] > 0
    assert sig["directional_concordance_btc_sol_pct"] == 100.0

    assert sig["simultaneous_eth_sol"] > 0
    assert sig["directional_concordance_eth_sol_pct"] == 100.0


def test_downside_correlation_active_vs_naive(cross_asset_data):
    """
    Verifies that downside correlation calculated only on active trading days
    is non-negative or negligible, refuting the naive calculation artifact.
    """
    ret = cross_asset_data["return_correlation"]
    active = ret["downside_correlation_active_only"]
    naive = ret["downside_correlation_naive"]

    # Naive is strongly negative due to 0-day artifact
    assert naive["btc_sol"] < -0.30

    # Active-only is much closer to zero or non-negative
    assert active["btc_sol"]["corr"] > -0.20
    assert active["btc_sol"]["sample_days"] > 10
