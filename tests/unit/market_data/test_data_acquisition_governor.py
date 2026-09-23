"""
Unit tests for DataAcquisitionGovernor.
"""

import pytest
from market_data.universal_data_fabric import UniversalMarketDataFabric
from market_data.data_acquisition_governor import DataAcquisitionGovernor
from market_data.primitives import OpportunityObservation, OpportunityType


def test_data_acquisition_governor_evaluation():
    fabric = UniversalMarketDataFabric()
    gov = DataAcquisitionGovernor(fabric)

    opp = OpportunityObservation(
        opportunity_id="OPP-CARRY-SOLUSDT-0001",
        opportunity_type=OpportunityType.FUNDING_ANOMALY,
        symbol="SOL/USDT",
        magnitude_score=0.85,
        description="Extreme funding detected",
        required_data_tokens=["FUNDING_RATE_HISTORY_SOLUSDT", "SPOT_PERP_BASIS_SOLUSDT"]
    )

    # Initially unavailable in fabric
    assert not gov.is_data_ready("FUNDING_RATE_HISTORY_SOLUSDT")

    # Evaluate and acquire
    gov.evaluate_and_acquire([opp])

    # Now should be ready via acquired tokens
    assert gov.is_data_ready("FUNDING_RATE_HISTORY_SOLUSDT")
    assert gov.is_data_ready("SPOT_PERP_BASIS_SOLUSDT")

    ready_ops = gov.filter_ready_opportunities([opp])
    assert len(ready_ops) == 1
    assert len(gov.get_acquired_tokens()) == 2

    # Check cryptographic lineage and lifecycle states
    report = gov.get_token_lineage_report()
    assert "FUNDING_RATE_HISTORY_SOLUSDT" in report
    token_record = report["FUNDING_RATE_HISTORY_SOLUSDT"]
    assert token_record["lifecycle_state"] == "AVAILABLE"
    assert len(token_record["lineage_hash"]) == 64  # SHA-256 hash
    assert token_record["source"] == "BINANCE_HISTORICAL_ARCHIVE"
    assert token_record["quality_status"] == "CERTIFIED"


def test_data_acquisition_governor_blocked_token():
    fabric = UniversalMarketDataFabric()
    gov = DataAcquisitionGovernor(fabric)

    opp = OpportunityObservation(
        opportunity_id="OPP-BLOCKED-0001",
        opportunity_type=OpportunityType.CROSS_EXCHANGE_DISLOCATION,
        symbol="BTC/USDT",
        magnitude_score=0.90,
        description="Unavailable external exchange feed",
        required_data_tokens=["UNAVAILABLE_OFFSHORE_FEED_BTC"]
    )

    gov.evaluate_and_acquire([opp])
    report = gov.get_token_lineage_report()
    assert "UNAVAILABLE_OFFSHORE_FEED_BTC" in report
    assert report["UNAVAILABLE_OFFSHORE_FEED_BTC"]["lifecycle_state"] == "BLOCKED_EXTERNAL_DATA"
    assert not gov.is_data_ready("UNAVAILABLE_OFFSHORE_FEED_BTC")
