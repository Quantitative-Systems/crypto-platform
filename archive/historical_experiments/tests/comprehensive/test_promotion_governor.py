"""
Comprehensive Test Suite: Promotion Governor & Strategy Graveyard.
Validates:
- 7-Tier canonical lifecycle transitions (RESEARCH -> CANDIDATE -> HISTORICAL_ROBUST -> FORWARD_HEALTHY -> PRODUCTION_QUALIFIED)
- Rejection of illegal shortcuts / manual bypass attempts
- Strict verification of empirical proofs
- Automated falsification routing to Strategy Graveyard
"""

import pytest
from platform_core.promotion_governor import (
    PromotionGovernor,
    CanonicalPromotionState,
    PromotionProof,
    IllegalPromotionBypassError,
)
from platform_core.evidence_provenance import ProvenanceClass


def test_valid_promotion_pipeline():
    gov = PromotionGovernor()
    strat_id = "FAM-TEST-ALPHA"
    gov.register_strategy(strat_id, CanonicalPromotionState.RESEARCH)

    # 1. RESEARCH -> CANDIDATE
    p1 = PromotionProof(
        proof_id="PROOF-1",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.CANDIDATE,
        evidence_hashes=["hash_dataset_123"],
        metrics={"hypothesis_length": 50},
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Hypothesis documented",
    )
    rec1 = gov.execute_transition(strat_id, CanonicalPromotionState.CANDIDATE, p1)
    assert rec1.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.CANDIDATE

    # 2. CANDIDATE -> HISTORICAL_ROBUST
    p2 = PromotionProof(
        proof_id="PROOF-2",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.HISTORICAL_ROBUST,
        evidence_hashes=["hash_backtest_456"],
        metrics={
            "trade_count": 120,
            "net_edge_r": 0.25,
            "windfall_adjusted_net_r": 0.08,
            "friction_shock_net_r": 0.12,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="DEV backtest passed all stress shocks",
    )
    rec2 = gov.execute_transition(strat_id, CanonicalPromotionState.HISTORICAL_ROBUST, p2)
    assert rec2.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.HISTORICAL_ROBUST


def test_illegal_shortcut_bypass_rejection():
    gov = PromotionGovernor()
    strat_id = "FAM-SHORTCUT"
    gov.register_strategy(strat_id, CanonicalPromotionState.RESEARCH)

    # Attempting to jump directly from RESEARCH to PRODUCTION_QUALIFIED
    p = PromotionProof(
        proof_id="PROOF-BYPASS",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.PRODUCTION_QUALIFIED,
        evidence_hashes=["fake_hash"],
        metrics={},
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Illegal bypass attempt",
    )

    with pytest.raises(IllegalPromotionBypassError) as exc_info:
        gov.execute_transition(strat_id, CanonicalPromotionState.PRODUCTION_QUALIFIED, p)
    assert "forbidden" in str(exc_info.value).lower()


def test_failed_windfall_audit_rejection():
    gov = PromotionGovernor()
    strat_id = "FAM-WINDFALL-FAIL"
    gov.register_strategy(strat_id, CanonicalPromotionState.CANDIDATE)

    # Net edge is positive, but windfall adjusted edge is negative (fails top 5% dropped test)
    p = PromotionProof(
        proof_id="PROOF-FAIL",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.HISTORICAL_ROBUST,
        evidence_hashes=["hash_789"],
        metrics={
            "trade_count": 100,
            "net_edge_r": 0.15,
            "windfall_adjusted_net_r": -0.05,  # Collapses without outliers
            "friction_shock_net_r": 0.02,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Fails windfall audit",
    )

    with pytest.raises(IllegalPromotionBypassError) as exc_info:
        gov.execute_transition(strat_id, CanonicalPromotionState.HISTORICAL_ROBUST, p)
    assert "windfall" in str(exc_info.value).lower()


def test_falsification_and_graveyard_routing():
    graveyard_records = []
    def mock_graveyard(strategy_id, reason, metrics):
        graveyard_records.append({"id": strategy_id, "reason": reason})

    gov = PromotionGovernor(graveyard_callback=mock_graveyard)
    strat_id = "FAM-FAIL-ALPHA"
    gov.register_strategy(strat_id, CanonicalPromotionState.RESEARCH)

    gov.falsify_strategy(strat_id, "Falsified by adverse slippage sensitivity")
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.FALSIFIED
    assert len(graveyard_records) == 1
    assert graveyard_records[0]["id"] == strat_id

    # Falsified alpha cannot be promoted anywhere
    p = PromotionProof("P", strat_id, CanonicalPromotionState.CANDIDATE, ["h"], {}, [ProvenanceClass.MEASURED_CERTIFIED_DATA.value], "")
    with pytest.raises(IllegalPromotionBypassError):
        gov.execute_transition(strat_id, CanonicalPromotionState.CANDIDATE, p)


def test_eabg_001_nine_verdict_lifecycle():
    """
    Directive EABG-001: Verifies the full 9-verdict economic lifecycle:
    UNTESTED -> PROMISING -> HISTORICALLY_ROBUST -> OOS_VALIDATED -> FORWARD_VALIDATED -> PRODUCTION_ELIGIBLE
    and FRAGILE branches.
    """
    gov = PromotionGovernor()
    strat_id = "FAM-EABG-001-STRAT"

    gov.register_strategy(strat_id, CanonicalPromotionState.UNTESTED)
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.UNTESTED

    # 1. UNTESTED -> PROMISING
    proof_promising = PromotionProof(
        proof_id="PROOF_PROMISING",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.PROMISING,
        evidence_hashes=["hash_candle_dataset_001"],
        metrics={"hypothesis_length": 55.0},
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Valid economic hypothesis documented",
    )
    rec1 = gov.execute_transition(strat_id, CanonicalPromotionState.PROMISING, proof_promising)
    assert rec1.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.PROMISING

    # 2. PROMISING -> HISTORICALLY_ROBUST
    proof_dev = PromotionProof(
        proof_id="PROOF_DEV",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.HISTORICALLY_ROBUST,
        evidence_hashes=["hash_dev_backtest_001"],
        metrics={
            "trade_count": 45,
            "net_edge_r": 1.25,
            "windfall_adjusted_net_r": 0.85,
            "friction_shock_net_r": 0.45,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="DEV backtest passes friction shock and windfall audit",
    )
    rec2 = gov.execute_transition(strat_id, CanonicalPromotionState.HISTORICALLY_ROBUST, proof_dev)
    assert rec2.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.HISTORICALLY_ROBUST

    # 3. HISTORICALLY_ROBUST -> OOS_VALIDATED
    proof_oos = PromotionProof(
        proof_id="PROOF_OOS",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.OOS_VALIDATED,
        evidence_hashes=["hash_oos_2024_001"],
        metrics={
            "oos_trade_count": 22,
            "oos_net_r": 0.52,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Out-of-sample positive return verified without parameter hunting",
    )
    rec3 = gov.execute_transition(strat_id, CanonicalPromotionState.OOS_VALIDATED, proof_oos)
    assert rec3.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.OOS_VALIDATED

    # 4. OOS_VALIDATED -> FORWARD_VALIDATED
    proof_fwd = PromotionProof(
        proof_id="PROOF_FWD",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.FORWARD_VALIDATED,
        evidence_hashes=["hash_fwd_telemetry_001"],
        metrics={
            "paper_days": 14,
            "duplicate_trades": 0,
            "telemetry_verified": 1,
            "fast_track_test_sim": 0,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="14 days forward paper execution without duplicates",
    )
    rec4 = gov.execute_transition(strat_id, CanonicalPromotionState.FORWARD_VALIDATED, proof_fwd)
    assert rec4.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.FORWARD_VALIDATED

    # 5. FORWARD_VALIDATED -> PRODUCTION_ELIGIBLE
    proof_prod = PromotionProof(
        proof_id="PROOF_PROD",
        strategy_id=strat_id,
        target_state=CanonicalPromotionState.PRODUCTION_ELIGIBLE,
        evidence_hashes=["hash_prod_signoff_001"],
        metrics={
            "risk_engine_veto": 0,
            "allocated_heat_pct": 1.20,
        },
        provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
        audit_notes="Production signoff with 1.20% heat allocation and $0.00 live capital",
    )
    rec5 = gov.execute_transition(strat_id, CanonicalPromotionState.PRODUCTION_ELIGIBLE, proof_prod)
    assert rec5.success is True
    assert gov.get_strategy_state(strat_id) == CanonicalPromotionState.PRODUCTION_ELIGIBLE

