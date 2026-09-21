"""
Tests for the QCP Hypothesis Research Registry governance infrastructure.

Tests cover:
    1. Valid hypothesis creation
    2. Unique hypothesis ID enforcement
    3. Invalid lifecycle transitions (including silent skip prevention)
    4. Valid lifecycle transitions (step-by-step)
    5. Registry YAML synchronization
    6. Missing required fields
    7. Malformed hypotheses
    8. Experiment-to-hypothesis cross-references
    9. Preservation of rejected hypotheses
    10. Prevention of duplicate IDs
    11. Prevention of accidental Validation/OOS promotion
    12. H-FRACTAL-01 specific assertions
    13. ID format validation
    14. Terminal state immutability
    15. Authorization-gated transitions
"""

import os
import tempfile
from pathlib import Path

import pytest

from hypotheses.hypothesis_governance import (
    AuthorizationRequiredError,
    DuplicateHypothesisIDError,
    HypothesisRegistry,
    HypothesisRegistryError,
    InvalidHypothesisIDError,
    InvalidTransitionError,
    LIFECYCLE_STATES,
    MalformedHypothesisError,
    MissingRequiredFieldError,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_record(
    hypothesis_id: str = "H-TEST-01",
    state: str = "PROPOSED",
) -> dict:
    """Return a minimally valid hypothesis record for testing."""
    return {
        "hypothesis_id": hypothesis_id,
        "title": "Test Hypothesis",
        "status": state,
        "lifecycle_state": state,
        "filesystem_path": f"hypotheses/proposed/{hypothesis_id}-test",
        "created_at": "2026-09-19",
        "updated_at": "2026-09-19",
        "owner": "QCP Research",
        "hypothesis_family": "TEST",
        "timeframe_sets": ["SET_1", "SET_2"],
        "asset_scope": "CONFIGURABLE",
        "bar_horizon": "CONFIGURABLE",
        "development_partition": {
            "period": "2021-01-01 to 2022-12-31",
            "role": "Development",
            "status": "ASSIGNED",
        },
        "validation_status": "NOT_STARTED",
        "oos_status": "UNTOUCHED",
        "related_experiments": [],
        "related_hypotheses": [],
    }


@pytest.fixture
def tmp_registry(tmp_path):
    """Return a HypothesisRegistry backed by a temp directory."""
    registry_file = tmp_path / "registry.yaml"
    return HypothesisRegistry(registry_path=registry_file)


@pytest.fixture
def registry_with_one(tmp_registry):
    """Return a registry pre-loaded with H-TEST-01 in PROPOSED state."""
    tmp_registry.register(_minimal_record("H-TEST-01", "PROPOSED"))
    return tmp_registry


# ---------------------------------------------------------------------------
# 1. Valid hypothesis creation
# ---------------------------------------------------------------------------

class TestValidCreation:
    def test_register_minimal_record(self, tmp_registry):
        tmp_registry.register(_minimal_record())
        assert tmp_registry.exists("H-TEST-01")

    def test_register_sets_updated_at(self, tmp_registry):
        tmp_registry.register(_minimal_record())
        h = tmp_registry.show("H-TEST-01")
        assert "updated_at" in h

    def test_register_multiple_hypotheses(self, tmp_registry):
        tmp_registry.register(_minimal_record("H-TEST-01"))
        tmp_registry.register(_minimal_record("H-TEST-02"))
        tmp_registry.register(_minimal_record("H-MOMENTUM-01"))
        assert len(tmp_registry.list_all()) == 3

    def test_register_fractal_family(self, tmp_registry):
        record = _minimal_record("H-FRACTAL-01")
        record["hypothesis_family"] = "FRACTAL"
        record["title"] = "Cross-Scale Mechanism Transfer"
        tmp_registry.register(record)
        h = tmp_registry.show("H-FRACTAL-01")
        assert h["hypothesis_family"] == "FRACTAL"
        assert h["title"] == "Cross-Scale Mechanism Transfer"


# ---------------------------------------------------------------------------
# 2. Unique hypothesis ID enforcement
# ---------------------------------------------------------------------------

class TestUniqueIDEnforcement:
    def test_duplicate_id_raises(self, registry_with_one):
        with pytest.raises(DuplicateHypothesisIDError):
            registry_with_one.register(_minimal_record("H-TEST-01"))

    def test_different_id_allowed(self, registry_with_one):
        registry_with_one.register(_minimal_record("H-TEST-02"))
        assert registry_with_one.exists("H-TEST-02")

    def test_id_availability_check(self, registry_with_one):
        assert not registry_with_one.is_id_available("H-TEST-01")
        assert registry_with_one.is_id_available("H-TEST-02")


# ---------------------------------------------------------------------------
# 3. Invalid lifecycle transitions (including silent skip prevention)
# ---------------------------------------------------------------------------

class TestInvalidTransitions:
    def test_cannot_skip_states(self, registry_with_one):
        """PROPOSED cannot jump to DEVELOPMENT_TEST."""
        with pytest.raises(InvalidTransitionError):
            registry_with_one.transition("H-TEST-01", "DEVELOPMENT_TEST")

    def test_cannot_skip_to_validation(self, registry_with_one):
        """PROPOSED cannot jump to VALIDATION."""
        with pytest.raises((InvalidTransitionError, AuthorizationRequiredError)):
            registry_with_one.transition("H-TEST-01", "VALIDATION")

    def test_cannot_skip_to_oos(self, registry_with_one):
        """PROPOSED cannot jump to OOS."""
        with pytest.raises((InvalidTransitionError, AuthorizationRequiredError)):
            registry_with_one.transition("H-TEST-01", "OOS")

    def test_cannot_skip_to_qualified(self, registry_with_one):
        """PROPOSED cannot jump to QUALIFIED."""
        with pytest.raises((InvalidTransitionError, AuthorizationRequiredError)):
            registry_with_one.transition("H-TEST-01", "QUALIFIED")

    def test_cannot_go_backwards(self, tmp_registry):
        """FORMALIZED cannot go back to PROPOSED."""
        rec = _minimal_record("H-TEST-01", "FORMALIZED")
        tmp_registry.register(rec)
        with pytest.raises(InvalidTransitionError):
            tmp_registry.transition("H-TEST-01", "PROPOSED")

    def test_unknown_target_state_raises(self, registry_with_one):
        with pytest.raises(InvalidTransitionError):
            registry_with_one.transition("H-TEST-01", "NONEXISTENT_STATE")

    def test_nonexistent_hypothesis_raises(self, tmp_registry):
        with pytest.raises(HypothesisRegistryError):
            tmp_registry.transition("H-DOES-NOT-EXIST-01", "FORMALIZED")


# ---------------------------------------------------------------------------
# 4. Valid lifecycle transitions (step-by-step)
# ---------------------------------------------------------------------------

class TestValidTransitions:
    def test_proposed_to_formalized(self, registry_with_one):
        registry_with_one.transition("H-TEST-01", "FORMALIZED")
        h = registry_with_one.show("H-TEST-01")
        assert h["lifecycle_state"] == "FORMALIZED"
        assert h["status"] == "FORMALIZED"

    def test_proposed_to_archived(self, registry_with_one):
        registry_with_one.transition("H-TEST-01", "ARCHIVED")
        h = registry_with_one.show("H-TEST-01")
        assert h["lifecycle_state"] == "ARCHIVED"

    def test_step_through_to_forensic_review(self, tmp_registry):
        """Verify step-by-step progression through pre-validation stages."""
        rec = _minimal_record("H-TEST-01", "PROPOSED")
        tmp_registry.register(rec)
        
        for from_state, to_state in [
            ("PROPOSED", "FORMALIZED"),
            ("FORMALIZED", "IMPLEMENTATION_READY"),
            ("IMPLEMENTATION_READY", "DEVELOPMENT_TEST"),
            ("DEVELOPMENT_TEST", "FORENSIC_REVIEW"),
        ]:
            tmp_registry.transition("H-TEST-01", to_state)
            h = tmp_registry.show("H-TEST-01")
            assert h["lifecycle_state"] == to_state, (
                f"After transitioning from {from_state}, expected {to_state} "
                f"but got {h['lifecycle_state']}"
            )

    def test_forensic_review_to_validation_candidate(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "FORENSIC_REVIEW")
        tmp_registry.register(rec)
        tmp_registry.transition("H-TEST-01", "VALIDATION_CANDIDATE")
        h = tmp_registry.show("H-TEST-01")
        assert h["lifecycle_state"] == "VALIDATION_CANDIDATE"

    def test_rejection_at_any_pre_validation_stage(self, tmp_registry):
        # Map each state to a unique valid H-<FAMILY>-<NUMBER> ID
        state_id_map = {
            "FORMALIZED":           "H-REJ-01",
            "IMPLEMENTATION_READY": "H-REJ-02",
            "DEVELOPMENT_TEST":     "H-REJ-03",
            "FORENSIC_REVIEW":      "H-REJ-04",
            "VALIDATION_CANDIDATE": "H-REJ-05",
        }
        for state, hid in state_id_map.items():
            rec = _minimal_record(hid, state)
            tmp_registry.register(rec)
            tmp_registry.transition(hid, "REJECTED")
            h = tmp_registry.show(hid)
            assert h["lifecycle_state"] == "REJECTED", (
                f"Expected REJECTED for {hid} (from {state}), got {h['lifecycle_state']}"
            )


# ---------------------------------------------------------------------------
# 5. Registry synchronization
# ---------------------------------------------------------------------------

class TestRegistrySync:
    def test_status_and_lifecycle_state_must_match(self, tmp_registry):
        rec = _minimal_record("H-TEST-01")
        rec["status"] = "PROPOSED"
        rec["lifecycle_state"] = "FORMALIZED"  # Mismatch!
        with pytest.raises(MalformedHypothesisError):
            tmp_registry.register(rec)

    def test_sync_check_clean_registry(self, registry_with_one):
        issues = registry_with_one.validate_registry_sync()
        assert issues == []

    def test_validate_registry_after_transition(self, registry_with_one):
        registry_with_one.transition("H-TEST-01", "FORMALIZED")
        issues = registry_with_one.validate_registry_sync()
        assert issues == []


# ---------------------------------------------------------------------------
# 6. Missing required fields
# ---------------------------------------------------------------------------

class TestMissingRequiredFields:
    def test_missing_hypothesis_id(self, tmp_registry):
        rec = _minimal_record()
        del rec["hypothesis_id"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_title(self, tmp_registry):
        rec = _minimal_record()
        del rec["title"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_lifecycle_state(self, tmp_registry):
        rec = _minimal_record()
        del rec["lifecycle_state"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_timeframe_sets(self, tmp_registry):
        rec = _minimal_record()
        del rec["timeframe_sets"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_development_partition(self, tmp_registry):
        rec = _minimal_record()
        del rec["development_partition"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_validation_status(self, tmp_registry):
        rec = _minimal_record()
        del rec["validation_status"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)

    def test_missing_related_experiments(self, tmp_registry):
        rec = _minimal_record()
        del rec["related_experiments"]
        with pytest.raises(MissingRequiredFieldError):
            tmp_registry.register(rec)


# ---------------------------------------------------------------------------
# 7. Malformed hypotheses
# ---------------------------------------------------------------------------

class TestMalformedHypotheses:
    def test_invalid_lifecycle_state_value(self, tmp_registry):
        rec = _minimal_record()
        rec["lifecycle_state"] = "MADE_UP_STATE"
        rec["status"] = "MADE_UP_STATE"
        with pytest.raises(MalformedHypothesisError):
            tmp_registry.register(rec)

    def test_empty_timeframe_sets_list(self, tmp_registry):
        rec = _minimal_record()
        rec["timeframe_sets"] = []
        with pytest.raises(MalformedHypothesisError):
            tmp_registry.register(rec)

    def test_timeframe_sets_not_list(self, tmp_registry):
        rec = _minimal_record()
        rec["timeframe_sets"] = "SET_1"
        with pytest.raises(MalformedHypothesisError):
            tmp_registry.register(rec)

    def test_related_experiments_not_list(self, tmp_registry):
        rec = _minimal_record()
        rec["related_experiments"] = "EXP-001"
        with pytest.raises(MalformedHypothesisError):
            tmp_registry.register(rec)


# ---------------------------------------------------------------------------
# 8. Experiment-to-hypothesis cross-references
# ---------------------------------------------------------------------------

class TestExperimentReferences:
    def test_add_experiment_reference(self, registry_with_one):
        registry_with_one.add_experiment_reference(
            "H-TEST-01",
            "EXP-H-TEST-01-20260919",
            description="Initial development sweep",
        )
        h = registry_with_one.show("H-TEST-01")
        assert len(h["related_experiments"]) == 1
        assert h["related_experiments"][0]["experiment_id"] == "EXP-H-TEST-01-20260919"
        assert h["latest_experiment"] == "EXP-H-TEST-01-20260919"

    def test_add_multiple_experiments(self, registry_with_one):
        registry_with_one.add_experiment_reference("H-TEST-01", "EXP-001")
        registry_with_one.add_experiment_reference("H-TEST-01", "EXP-002")
        h = registry_with_one.show("H-TEST-01")
        assert len(h["related_experiments"]) == 2
        assert h["latest_experiment"] == "EXP-002"

    def test_add_experiment_to_nonexistent_hypothesis_raises(self, tmp_registry):
        with pytest.raises(HypothesisRegistryError):
            tmp_registry.add_experiment_reference("H-NONEXISTENT-01", "EXP-001")

    def test_record_result(self, registry_with_one):
        registry_with_one.add_experiment_reference("H-TEST-01", "EXP-001")
        registry_with_one.record_result(
            "H-TEST-01",
            "EXP-001",
            "net_r=-5.2R, expectancy=-0.3R, PF=0.72",
        )
        h = registry_with_one.show("H-TEST-01")
        assert h["latest_result"] == "net_r=-5.2R, expectancy=-0.3R, PF=0.72"


# ---------------------------------------------------------------------------
# 9. Preservation of rejected hypotheses
# ---------------------------------------------------------------------------

class TestRejectedPreservation:
    def test_rejected_hypothesis_is_preserved(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "FORMALIZED")
        tmp_registry.register(rec)
        tmp_registry.transition("H-TEST-01", "REJECTED")
        
        # Hypothesis must still be in the registry
        assert tmp_registry.exists("H-TEST-01")
        h = tmp_registry.show("H-TEST-01")
        assert h["lifecycle_state"] == "REJECTED"

    def test_rejected_hypothesis_immutable(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "FORMALIZED")
        tmp_registry.register(rec)
        tmp_registry.transition("H-TEST-01", "REJECTED")
        
        # Cannot transition out of REJECTED
        with pytest.raises(InvalidTransitionError):
            tmp_registry.transition("H-TEST-01", "PROPOSED")

    def test_invalidated_hypothesis_preserved(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "VALIDATION")
        tmp_registry.register(rec)
        # Validation → Invalidated is a valid terminal transition
        tmp_registry.transition("H-TEST-01", "INVALIDATED")
        
        assert tmp_registry.exists("H-TEST-01")
        h = tmp_registry.show("H-TEST-01")
        assert h["lifecycle_state"] == "INVALIDATED"

    def test_rejected_id_cannot_be_reused(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "FORMALIZED")
        tmp_registry.register(rec)
        tmp_registry.transition("H-TEST-01", "REJECTED")
        
        # Attempting to register a new hypothesis with the same ID must fail
        with pytest.raises(DuplicateHypothesisIDError):
            tmp_registry.register(_minimal_record("H-TEST-01", "PROPOSED"))


# ---------------------------------------------------------------------------
# 10. Prevention of duplicate IDs
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    def test_cannot_register_same_id_twice(self, tmp_registry):
        tmp_registry.register(_minimal_record("H-TEST-01"))
        with pytest.raises(DuplicateHypothesisIDError):
            tmp_registry.register(_minimal_record("H-TEST-01"))

    def test_next_sequential_id_works(self, tmp_registry):
        tmp_registry.register(_minimal_record("H-TEST-01"))
        tmp_registry.register(_minimal_record("H-TEST-02"))
        assert len(tmp_registry.list_all()) == 2


# ---------------------------------------------------------------------------
# 11. Prevention of accidental Validation/OOS promotion
# ---------------------------------------------------------------------------

class TestValidationOOSProtection:
    def test_validation_candidate_to_validation_requires_auth(self, tmp_registry):
        """transition() must NOT allow VALIDATION_CANDIDATE → VALIDATION."""
        rec = _minimal_record("H-TEST-01", "VALIDATION_CANDIDATE")
        tmp_registry.register(rec)
        with pytest.raises(AuthorizationRequiredError):
            tmp_registry.transition("H-TEST-01", "VALIDATION")

    def test_validation_to_oos_requires_auth(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "VALIDATION")
        tmp_registry.register(rec)
        with pytest.raises(AuthorizationRequiredError):
            tmp_registry.transition("H-TEST-01", "OOS")

    def test_oos_to_qualified_requires_auth(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "OOS")
        tmp_registry.register(rec)
        with pytest.raises(AuthorizationRequiredError):
            tmp_registry.transition("H-TEST-01", "QUALIFIED")

    def test_authorized_transition_validation_requires_nonempty_token(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "VALIDATION_CANDIDATE")
        tmp_registry.register(rec)
        with pytest.raises(ValueError):
            tmp_registry.transition_authorized(
                "H-TEST-01",
                "VALIDATION",
                authorization_token="",
                authorization_rationale="Some rationale",
            )

    def test_authorized_transition_validation_requires_nonempty_rationale(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "VALIDATION_CANDIDATE")
        tmp_registry.register(rec)
        with pytest.raises(ValueError):
            tmp_registry.transition_authorized(
                "H-TEST-01",
                "VALIDATION",
                authorization_token="TOKEN-001",
                authorization_rationale="",
            )

    def test_authorized_transition_succeeds_with_valid_inputs(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "VALIDATION_CANDIDATE")
        tmp_registry.register(rec)
        tmp_registry.transition_authorized(
            "H-TEST-01",
            "VALIDATION",
            authorization_token="GOVERNANCE-TOKEN-001",
            authorization_rationale="Development results passed pre-registered thresholds. "
                                     "Forensic review clean. Governance approved.",
        )
        h = tmp_registry.show("H-TEST-01")
        assert h["lifecycle_state"] == "VALIDATION"
        assert "authorization_log" in h
        assert len(h["authorization_log"]) == 1


# ---------------------------------------------------------------------------
# 12. H-FRACTAL-01 specific assertions
# ---------------------------------------------------------------------------

class TestHFractal01:
    """Tests specific to the H-FRACTAL-01 registration in the actual registry.yaml."""

    def _load_real_registry(self) -> HypothesisRegistry:
        """Load the actual hypotheses/registry.yaml."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        registry_path = repo_root / "hypotheses" / "registry.yaml"
        return HypothesisRegistry(registry_path=registry_path)

    def test_h_fractal_01_is_registered(self):
        registry = self._load_real_registry()
        assert registry.exists("H-FRACTAL-01"), (
            "H-FRACTAL-01 must be registered in hypotheses/registry.yaml"
        )

    def test_h_fractal_01_id_format(self):
        HypothesisRegistry.validate_id_format("H-FRACTAL-01")  # must not raise

    def test_h_fractal_01_status_is_formalized(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert h["lifecycle_state"] == "FORMALIZED"

    def test_h_fractal_01_has_all_required_fields(self):
        registry = self._load_real_registry()
        errors = registry.validate_hypothesis("H-FRACTAL-01")
        assert errors == [], f"H-FRACTAL-01 validation errors: {errors}"

    def test_h_fractal_01_has_six_timeframe_sets(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert set(h["timeframe_sets"]) == {"SET_1", "SET_2", "SET_3", "SET_4", "SET_5", "SET_6"}

    def test_h_fractal_01_is_not_in_validation(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert h["lifecycle_state"] not in {"VALIDATION", "OOS", "QUALIFIED"}, (
            "H-FRACTAL-01 must NOT be in VALIDATION, OOS, or QUALIFIED state at initial registration."
        )

    def test_h_fractal_01_oos_is_untouched(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert h.get("oos_status") in {"UNTOUCHED", "NOT_STARTED"}, (
            "OOS partition must be untouched at initial registration."
        )

    def test_h_fractal_01_has_no_results_yet(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert h.get("latest_experiment") is None
        assert h.get("decision") is None

    def test_h_fractal_01_family_is_fractal(self):
        registry = self._load_real_registry()
        h = registry.show("H-FRACTAL-01")
        assert h["hypothesis_family"] == "FRACTAL"

    def test_h_fractal_01_cannot_be_promoted_to_validation_without_auth(self):
        """
        Even if we step H-FRACTAL-01 through to VALIDATION_CANDIDATE in a temp registry,
        promotion to VALIDATION must require authorization.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = HypothesisRegistry(registry_path=Path(tmpdir) / "registry.yaml")
            rec = _minimal_record("H-FRACTAL-01", "VALIDATION_CANDIDATE")
            rec["hypothesis_family"] = "FRACTAL"
            reg.register(rec)
            with pytest.raises(AuthorizationRequiredError):
                reg.transition("H-FRACTAL-01", "VALIDATION")

    def test_h_fractal_01_registry_sync_is_clean(self):
        registry = self._load_real_registry()
        issues = registry.validate_registry_sync()
        assert issues == [], f"Registry sync issues: {issues}"


# ---------------------------------------------------------------------------
# 13. ID format validation
# ---------------------------------------------------------------------------

class TestIDFormatValidation:
    def test_valid_ids(self):
        valid = [
            "H-FRACTAL-01",
            "H-MOMENTUM-01",
            "H-REVERSION-99",
            "H-VOLATILITY-001",
            "H-AB-01",
        ]
        for hid in valid:
            HypothesisRegistry.validate_id_format(hid)  # must not raise

    def test_invalid_ids(self):
        invalid = [
            "FRACTAL-01",          # missing H- prefix
            "H-fractal-01",        # lowercase family
            "H-FRACTAL",           # missing number
            "H-FRACTAL-",          # trailing dash, no number
            "H-01",                # missing family
            "H--01",               # empty family
            "H-FRACTAL-1234",      # 4-digit number (too long)
            "H-F-01",              # family too short (< 2 chars)
            "H-FRACTAL-01-EXTRA",  # extra segment
            "",                    # empty
            "H-FRACTAL_01",        # underscore instead of dash
        ]
        for hid in invalid:
            with pytest.raises(InvalidHypothesisIDError, match=hid if hid else ""):
                HypothesisRegistry.validate_id_format(hid)


# ---------------------------------------------------------------------------
# 14. Terminal state immutability
# ---------------------------------------------------------------------------

class TestTerminalStateImmutability:
    @pytest.mark.parametrize("terminal_state", list(TERMINAL_STATES))
    def test_terminal_states_cannot_transition(self, tmp_registry, terminal_state):
        rec = _minimal_record("H-TEST-01", terminal_state)
        tmp_registry.register(rec)
        
        # Try every possible target state
        for target in LIFECYCLE_STATES:
            if target != terminal_state:
                with pytest.raises((InvalidTransitionError, AuthorizationRequiredError)):
                    tmp_registry.transition("H-TEST-01", target)


# ---------------------------------------------------------------------------
# 15. Valid transitions coverage
# ---------------------------------------------------------------------------

class TestTransitionCoverage:
    def test_all_lifecycle_states_defined(self):
        for state in LIFECYCLE_STATES:
            assert state in VALID_TRANSITIONS, (
                f"Lifecycle state {state!r} has no entry in VALID_TRANSITIONS."
            )

    def test_terminal_states_have_no_outgoing_transitions(self):
        for state in TERMINAL_STATES:
            assert VALID_TRANSITIONS[state] == [], (
                f"Terminal state {state!r} must have empty transition list."
            )

    def test_get_valid_transitions_returns_list(self, registry_with_one):
        result = registry_with_one.get_valid_transitions("H-TEST-01")
        assert isinstance(result, list)
        assert "FORMALIZED" in result  # PROPOSED can transition to FORMALIZED

    def test_get_valid_transitions_for_terminal(self, tmp_registry):
        rec = _minimal_record("H-TEST-01", "REJECTED")
        tmp_registry.register(rec)
        result = tmp_registry.get_valid_transitions("H-TEST-01")
        assert result == []
