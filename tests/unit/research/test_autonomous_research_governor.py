"""
Unit tests for AutonomousResearchGovernor and Alpha Factory integration.
"""

import os
import tempfile
import pytest
from market_intelligence.opportunity_detector import OpportunityObservation, OpportunityType
from research.opportunity_memory import OpportunityMemory
from research.autonomous_research_governor import AutonomousResearchGovernor
from research.autonomous_research_factory import AutonomousResearchFactory


@pytest.fixture
def temp_memory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    mem = OpportunityMemory(db_path=db_path)
    yield mem
    if os.path.exists(db_path):
        os.remove(db_path)


def test_research_governor_and_factory_flow(temp_memory):
    governor = AutonomousResearchGovernor(temp_memory)
    factory = AutonomousResearchFactory()

    opps = [
        OpportunityObservation(
            opportunity_id="OPP-CARRY-SOLUSDT-0001",
            opportunity_type=OpportunityType.FUNDING_ANOMALY,
            symbol="SOL/USDT",
            magnitude_score=0.90,
            description="Extreme funding detected",
            required_data_tokens=["FUNDING_RATE_HISTORY_SOLUSDT"]
        ),
        OpportunityObservation(
            opportunity_id="OPP-OFI-SOLUSDT-0002",
            opportunity_type=OpportunityType.LIQUIDITY_IMBALANCE,
            symbol="SOL/USDT",
            magnitude_score=0.75,
            description="Order book skew detected",
            required_data_tokens=["ORDER_BOOK_L2_SOLUSDT"]
        )
    ]

    hypotheses = governor.formulate_hypotheses(opps)
    assert len(hypotheses) == 2
    assert hypotheses[0].target_family == "CARRY"
    assert hypotheses[1].target_family == "MICROSTRUCTURE"
    assert hypotheses[1].timeframe == "1m"

    candidates = factory.generate_candidate_population(hypotheses)
    assert len(candidates) == 2
    for c in candidates:
        assert c.performance.net_edge_r == 0.0  # Zero asserted performance
        assert c.evidence_hash != ""
        assert len(c.features) >= 1
        assert isinstance(c.failure_modes, list)


def test_research_governor_dynamic_prioritization_sensitivity(temp_memory):
    governor = AutonomousResearchGovernor(temp_memory)

    # 1. Sensitivity to magnitude
    high_mag_opp = OpportunityObservation(
        opportunity_id="OPP-HIGH-01",
        opportunity_type=OpportunityType.FUNDING_ANOMALY,
        symbol="BTC/USDT",
        magnitude_score=0.95,
        description="High magnitude",
        required_data_tokens=["FUNDING_RATE_HISTORY_BTCUSDT"]
    )
    low_mag_opp = OpportunityObservation(
        opportunity_id="OPP-LOW-01",
        opportunity_type=OpportunityType.FUNDING_ANOMALY,
        symbol="ETH/USDT",
        magnitude_score=0.20,
        description="Low magnitude",
        required_data_tokens=["FUNDING_RATE_HISTORY_ETHUSDT"]
    )

    hyp_high = governor.formulate_hypotheses([high_mag_opp])[0]
    hyp_low = governor.formulate_hypotheses([low_mag_opp])[0]

    assert hyp_high.priority_score > hyp_low.priority_score
    assert hyp_high.scoring_components["magnitude"] > hyp_low.scoring_components["magnitude"]

    # 2. Sensitivity to memory failure history
    # Record failure for CARRY BTC/USDT
    temp_memory.record_hypothesis_evaluation(
        alpha_id="HYP-FAIL-BTC",
        opportunity_type="CARRY",
        symbol="BTC/USDT",
        timeframe="4h",
        falsified=True,
        failure_reason="Friction overwhelmed edge",
        net_edge_r=-0.12
    )

    hyp_after_failure = governor.formulate_hypotheses([high_mag_opp])[0]
    # Memory penalty reduces novelty score
    assert hyp_after_failure.scoring_components["novelty"] < hyp_high.scoring_components["novelty"]
    assert hyp_after_failure.priority_score < hyp_high.priority_score
