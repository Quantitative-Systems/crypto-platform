"""Unit tests for Hypothesis Registry and Concept Drift Detector."""
from market_intelligence.hypotheses.concept_drift import (
    ConceptDriftDetector,
    DriftSeverity,
)
from market_intelligence.hypotheses.hypothesis_registry import (
    CausalHypothesis,
    HypothesisRegistry,
    HypothesisStatus,
    ValidationVerdict,
)


def test_hypothesis_validation_lifecycle():
    registry = HypothesisRegistry()

    hyp = CausalHypothesis(
        hypothesis_id="H-MACRO-CPI-001",
        name="CPI Surprise Transmission",
        observation="CPI downside surprise fuels risk-on rally",
        mechanism="Downside CPI -> Lower Yields -> USD down -> BTC continuation",
        affected_assets=["BTCUSDT", "ETHUSDT"],
        regime_conditions={"volatility": "NORMAL", "risk": "RISK_ON"},
        expected_effect="Increases bull continuation win rate",
        expected_expectancy_r=1.25,
        expected_win_rate=0.62,
    )
    registry.register(hyp)

    # Initial status is CANDIDATE; cannot be promoted directly without DEV/VAL/OOS
    assert hyp.status == HypothesisStatus.CANDIDATE
    assert registry.promote_to_active(hyp.hypothesis_id) is False

    # Simulate passing DEV & VAL, but OOS still PENDING
    hyp.dev_verdict = ValidationVerdict.PASS
    hyp.val_verdict = ValidationVerdict.PASS
    assert registry.promote_to_active(hyp.hypothesis_id) is False

    # Simulate passing OOS -> Full certification achieved
    hyp.oos_verdict = ValidationVerdict.PASS
    assert hyp.is_fully_validated() is True
    assert registry.promote_to_active(hyp.hypothesis_id) is True
    assert hyp.status == HypothesisStatus.ACTIVE


def test_concept_drift_detector():
    registry = HypothesisRegistry()
    hyp = CausalHypothesis(
        hypothesis_id="H-POS-FUNDING-001",
        name="Funding Squeeze Edge",
        observation="Negative funding in bull continuation squeezes higher",
        mechanism="Trapped shorts fuel displacement",
        affected_assets=["BTCUSDT"],
        regime_conditions={},
        expected_effect="High edge",
        expected_expectancy_r=1.50,
        expected_win_rate=0.65,
        dev_verdict=ValidationVerdict.PASS,
        val_verdict=ValidationVerdict.PASS,
        oos_verdict=ValidationVerdict.PASS,
        status=HypothesisStatus.ACTIVE,
    )
    registry.register(hyp)

    detector = ConceptDriftDetector(registry, min_sample_size=10)

    # Case 1: Healthy performance matching distribution
    healthy_results = [1.5, -1.0, 2.0, 1.2, -1.0, 3.0, 1.8, -1.0, 2.5, 1.0] # Sum ~ 10.0 / 10 = +1.0R, 70% WR
    report_healthy = detector.monitor_hypothesis("H-POS-FUNDING-001", healthy_results)
    assert report_healthy.severity == DriftSeverity.NORMAL
    assert hyp.status == HypothesisStatus.ACTIVE

    # Case 2: Severe decay (Negative expectancy) -> Triggers DEGRADATION & SUSPENSION
    decayed_results = [-1.0, -1.0, -1.0, 0.5, -1.0, -1.0, -1.0, 0.2, -1.0, -1.0] # Average < 0
    report_decay = detector.monitor_hypothesis("H-POS-FUNDING-001", decayed_results)
    assert report_decay.severity == DriftSeverity.DEGRADATION
    assert hyp.status == HypothesisStatus.SUSPENDED
    assert "Degradation" in hyp.meta.get("suspension_reason", "")
