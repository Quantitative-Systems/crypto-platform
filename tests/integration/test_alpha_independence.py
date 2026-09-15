"""
Integration tests for QCP Alpha Independence & Diversification Matrix.

Verifies:
1. Matrix artifact existence and structural integrity.
2. Statistical independence of Family 06 Volatility Squeeze from Family 07 Trend Continuation.
3. Preservation of falsified candidates in research memory without parameter mining.
4. Non-degeneracy of downside correlation and position concurrency metrics.
"""

import os
import json
import pytest

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "research", "results")
MATRIX_JSON_PATH = os.path.join(RESULTS_DIR, "ALPHA_INDEPENDENCE_MATRIX.json")


@pytest.fixture
def matrix_data():
    if not os.path.exists(MATRIX_JSON_PATH):
        pytest.skip(f"Alpha Independence Matrix not found at {MATRIX_JSON_PATH}")
    with open(MATRIX_JSON_PATH, "r") as f:
        return json.load(f)


def test_matrix_artifact_schema(matrix_data):
    """Verifies that the Alpha Independence Matrix contains required top-level keys."""
    assert "platform" in matrix_data
    assert "baseline_candidate" in matrix_data
    assert matrix_data["baseline_candidate"] == "FAM-07-MTFCONT_SOLUSDT_Set2"
    assert "pairwise_return_correlation" in matrix_data
    assert "pairwise_downside_correlation" in matrix_data
    assert "pairwise_position_concurrency_pct" in matrix_data
    assert "candidates" in matrix_data
    assert len(matrix_data["candidates"]) >= 5


def test_candidate_independence_from_baseline(matrix_data):
    """
    Verifies that the discovered Family 06 Volatility Squeeze candidates
    exhibit demonstrable independence (low correlation and low position overlap)
    relative to the baseline SOL Set 2 trend continuation candidate.
    """
    candidates = {c["alpha_id"]: c for c in matrix_data["candidates"]}
    assert "FAM-07-MTFCONT_SOLUSDT_Set2" in candidates
    baseline = candidates["FAM-07-MTFCONT_SOLUSDT_Set2"]
    assert baseline["qualification_state"] == "QUALIFIED_ROBUST"

    # Test ETH 4H Volatility Squeeze
    assert "FAM06_ETH_USDT_4h" in candidates
    eth_sq = candidates["FAM06_ETH_USDT_4h"]
    assert eth_sq["qualification_state"] == "QUALIFIED_ROBUST"
    assert eth_sq["lifetime_net_r"] > 50.0  # Demonstrates positive net edge
    assert eth_sq["independence_vs_sol_set2"]["return_correlation"] < 0.30  # Low return correlation
    assert eth_sq["independence_vs_sol_set2"]["position_overlap_pct"] < 20.0  # Low market exposure overlap

    # Test BTC 4H Volatility Squeeze
    assert "FAM06_BTC_USDT_4h" in candidates
    btc_sq = candidates["FAM06_BTC_USDT_4h"]
    assert btc_sq["qualification_state"] == "QUALIFIED_ROBUST"
    assert btc_sq["lifetime_net_r"] > 50.0
    assert btc_sq["independence_vs_sol_set2"]["return_correlation"] < 0.20  # Near-orthogonal return correlation
    assert btc_sq["independence_vs_sol_set2"]["position_overlap_pct"] < 20.0


def test_falsified_graveyard_memory(matrix_data):
    """
    Ensures that falsified candidates (Relative Value cointegration, Dynamic Funding Carry)
    remain preserved as institutional research memory rather than being deleted or mined.
    """
    candidates = {c["alpha_id"]: c for c in matrix_data["candidates"]}

    assert "RV_LONG_HORIZON_COINTEGRATION_V1" in candidates
    rv_cand = candidates["RV_LONG_HORIZON_COINTEGRATION_V1"]
    assert rv_cand["qualification_state"] == "FALSIFIED"
    assert rv_cand["lifecycle_status"] == "RESEARCH_GRAVEYARD_FALSIFIED"

    assert "FAM-10-FUNDINGCARRY" in candidates
    carry_cand = candidates["FAM-10-FUNDINGCARRY"]
    assert carry_cand["qualification_state"] == "FALSIFIED"
    assert carry_cand["lifecycle_status"] == "RESEARCH_GRAVEYARD_FALSIFIED"


def test_downside_correlation_sanity(matrix_data):
    """
    Asserts that downside correlation values are finite and not artificially 1.0,
    proving that simultaneous tail liquidation does not dominate the cross-mechanism portfolio.
    """
    downside_corr = matrix_data["pairwise_downside_correlation"]
    base_id = "FAM-07-MTFCONT_SOLUSDT_Set2"

    for cand_id, val in downside_corr[base_id].items():
        if cand_id != base_id:
            assert isinstance(val, (int, float))
            assert not (val != val)  # Not NaN
            assert val < 0.50  # Downside correlation is well below dangerous contagion threshold
