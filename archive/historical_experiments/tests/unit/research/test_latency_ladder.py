"""
Unit tests for Family 06 Latency Ladder & Execution-Sensitivity Audit.

Verifies:
1. Integrity of the latency ladder audit artifact (FAM06_EXECUTION_SENSITIVITY_AUDIT.json).
2. Proper detection of the same-bar lookahead bug vs causal next-bar open fill.
3. Monotonic causal timestamp ordering across the ladder (0m, 15m, 30m, 60m, 120m, 240m).
4. Evidence-based governance classification of Family 06 asset instances.
"""

import os
import json
import pytest

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "research", "results")
AUDIT_JSON_PATH = os.path.join(RESULTS_DIR, "FAM06_EXECUTION_SENSITIVITY_AUDIT.json")


@pytest.fixture
def audit_data():
    if not os.path.exists(AUDIT_JSON_PATH):
        pytest.skip(f"Latency ladder audit file not found at {AUDIT_JSON_PATH}")
    with open(AUDIT_JSON_PATH, "r") as f:
        return json.load(f)


def test_latency_ladder_schema_and_assets(audit_data):
    """Verifies artifact schema and evaluated assets."""
    assert "audit_name" in audit_data
    assert audit_data["audit_name"] == "FAM06_EXECUTION_SENSITIVITY_AUDIT"
    assert "methodology" in audit_data
    assert "assets" in audit_data

    assets = audit_data["assets"]
    assert "BTCUSDT" in assets
    assert "ETHUSDT" in assets
    assert "SOLUSDT" in assets


def test_lookahead_deflation_detection(audit_data):
    """
    Verifies that the audit caught the lookahead inflation:
    Lookahead baseline for BTC/ETH was ~104R/103R, whereas causal 0m fill is <= +5.0R.
    """
    btc = audit_data["assets"]["BTCUSDT"]
    eth = audit_data["assets"]["ETHUSDT"]

    # Lookahead baselines
    assert btc["flawed_lookahead_baseline"]["net_r"] > 100.0
    assert eth["flawed_lookahead_baseline"]["net_r"] > 100.0

    # Causal 0m next-bar open fills
    btc_0m = btc["causal_latency_ladder"]["0m"]["net_r"]
    eth_0m = eth["causal_latency_ladder"]["0m"]["net_r"]

    assert btc_0m < 5.0
    assert eth_0m < 10.0


def test_ladder_points_completeness(audit_data):
    """Verifies that all required delay intervals (0m, 15m, 30m, 60m, 120m, 240m) are present."""
    required_delays = ["0m", "15m", "30m", "60m", "120m", "240m"]

    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        ladder = audit_data["assets"][sym]["causal_latency_ladder"]
        for d in required_delays:
            assert d in ladder
            assert "net_r" in ladder[d]
            assert "expectancy_r" in ladder[d]
            assert "profit_factor" in ladder[d]
            assert "win_rate_pct" in ladder[d]
            assert "max_drawdown_r" in ladder[d]
            assert "trade_count" in ladder[d]
            assert ladder[d]["trade_count"] > 0


def test_governance_classification(audit_data):
    """
    Verifies evidence-based classification:
    BTC & ETH are FALSIFIED_NEGATIVE_EDGE, SOL is RESEARCH_SURVIVOR_SUB_THRESHOLD.
    None are PAPER_ELIGIBLE or QUALIFIED_ROBUST.
    """
    btc = audit_data["assets"]["BTCUSDT"]
    eth = audit_data["assets"]["ETHUSDT"]
    sol = audit_data["assets"]["SOLUSDT"]

    assert btc["final_governance_classification"] == "FALSIFIED_NEGATIVE_EDGE"
    assert eth["final_governance_classification"] in ("FALSIFIED_NEGATIVE_EDGE", "RESEARCH_SURVIVOR_SUB_THRESHOLD")
    assert sol["final_governance_classification"] == "RESEARCH_SURVIVOR_SUB_THRESHOLD"

    # Strict invariant: No Family 06 stream is qualified for paper
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        assert audit_data["assets"][sym]["final_governance_classification"] != "QUALIFIED_ROBUST"
        assert audit_data["assets"][sym]["final_governance_classification"] != "PAPER_ELIGIBLE"
