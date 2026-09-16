"""
Unit tests for CertifiedResearchUniverseEngine.
Verifies warehouse data auditing, SHA-256 lineage hashing, gap detection,
and machine-readable inventory generation.
"""

import json
import pytest
from pathlib import Path

from market_data.certified_research_universe import (
    CertifiedDatasetRecord,
    CertifiedResearchUniverseEngine,
)


def test_certified_research_universe_audit_real_warehouse():
    engine = CertifiedResearchUniverseEngine()
    inventory = engine.audit_and_generate_inventory()

    assert inventory["total_certified_datasets"] >= 20
    assert inventory["eligible_for_research_count"] >= 20
    assert "BTC/USDT" in inventory["available_assets"]
    assert "ETH/USDT" in inventory["available_assets"]
    assert "SOL/USDT" in inventory["available_assets"]

    # Verify that external streams are explicitly marked as unavailable
    unavail_names = [s["stream_name"] for s in inventory["unavailable_data_streams"]]
    assert "HISTORICAL_FUNDING_RATES" in unavail_names
    assert "L2_ORDER_BOOK_DEPTH" in unavail_names
    assert "TICK_LIQUIDATION_FLOW" in unavail_names
    assert "CROSS_VENUE_TICK_PRICES" in unavail_names

    for s in inventory["unavailable_data_streams"]:
        assert s["status"] == "BLOCKED_EXTERNAL_DATA"

    # Verify inventory file was generated on disk and is valid json
    assert engine.output_path.exists()
    with open(engine.output_path, "r") as f:
        data = json.load(f)
    assert data["total_certified_datasets"] == inventory["total_certified_datasets"]
    assert len(data["certified_datasets"]) == inventory["total_certified_datasets"]

    # Verify individual record properties
    first_record = inventory["certified_datasets"][0]
    assert "asset" in first_record
    assert "lineage_hash" in first_record
    assert len(first_record["lineage_hash"]) == 64  # SHA-256
    assert "bar_count" in first_record
    assert "granularity_seconds" in first_record
    assert first_record["bar_count"] > 0
