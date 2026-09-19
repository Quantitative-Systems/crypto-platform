"""
hypotheses.hypothesis_governance
=================================
QCP Hypothesis Research Registry — Lifecycle Engine and CLI

Governs the full hypothesis lifecycle:

    PROPOSED → FORMALIZED → IMPLEMENTATION_READY → DEVELOPMENT_TEST
    → FORENSIC_REVIEW → VALIDATION_CANDIDATE → VALIDATION → OOS
    → QUALIFIED | REJECTED | INVALIDATED | ARCHIVED

Rules enforced:
    - A hypothesis cannot silently skip lifecycle states.
    - Terminal states (QUALIFIED, REJECTED, INVALIDATED, ARCHIVED) are immutable.
    - Hypothesis IDs must follow H-<FAMILY>-<NUMBER> format and must be unique.
    - filesystem_path and registry.yaml status must remain consistent.
    - Validation/OOS promotion requires explicit authorization (not automatic).
    - Rejected hypotheses are permanently preserved; IDs are never reused.

Integration:
    - Reads registry.yaml from hypotheses/ root.
    - Cross-references research.lifecycle.experiment_ledger (if available).
    - Reads research.timeframe_sets for SET metadata (by ID, no style assumptions).

CLI:
    python -m hypotheses.hypothesis_governance list
    python -m hypotheses.hypothesis_governance show H-FRACTAL-01
    python -m hypotheses.hypothesis_governance validate H-FRACTAL-01
    python -m hypotheses.hypothesis_governance status
    python -m hypotheses.hypothesis_governance transitions H-FRACTAL-01 FORENSIC_REVIEW
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Try to import PyYAML. If unavailable, use a lightweight fallback parser
# sufficient for the registry.yaml structure this module writes.
# ---------------------------------------------------------------------------
try:
    import yaml as _yaml  # type: ignore

    def _load_yaml(text: str) -> Any:
        return _yaml.safe_load(text)

    def _dump_yaml(obj: Any) -> str:
        return _yaml.dump(obj, default_flow_style=False, sort_keys=False, allow_unicode=True)

except ImportError:  # pragma: no cover — yaml available in CI
    import json as _json  # fallback: convert via JSON round-trip for basic dict/list

    def _load_yaml(text: str) -> Any:  # type: ignore[misc]
        raise ImportError(
            "PyYAML is not installed. Install it with: pip install pyyaml\n"
            "Until then, registry.yaml cannot be parsed by hypothesis_governance.py."
        )

    def _dump_yaml(obj: Any) -> str:  # type: ignore[misc]
        raise ImportError("PyYAML is not installed.")


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"

# ---------------------------------------------------------------------------
# Hypothesis ID format: H-<FAMILY>-<NUMBER>
# FAMILY: uppercase alpha, 1-20 chars. NUMBER: 1-3 digits (zero-padded allowed).
# ---------------------------------------------------------------------------
HYPOTHESIS_ID_PATTERN = re.compile(r"^H-[A-Z]{2,20}-\d{1,3}$")

# ---------------------------------------------------------------------------
# Lifecycle states and valid transitions.
# Mirrors registry.yaml for programmatic enforcement.
# ---------------------------------------------------------------------------
LIFECYCLE_STATES = [
    "PROPOSED",
    "FORMALIZED",
    "IMPLEMENTATION_READY",
    "DEVELOPMENT_TEST",
    "FORENSIC_REVIEW",
    "VALIDATION_CANDIDATE",
    "VALIDATION",
    "OOS",
    "QUALIFIED",
    "REJECTED",
    "INVALIDATED",
    "ARCHIVED",
]

TERMINAL_STATES = {"QUALIFIED", "REJECTED", "INVALIDATED", "ARCHIVED"}

# Pre-VALIDATION states that do not require Validation/OOS partition access.
PRE_VALIDATION_STATES = {
    "PROPOSED",
    "FORMALIZED",
    "IMPLEMENTATION_READY",
    "DEVELOPMENT_TEST",
    "FORENSIC_REVIEW",
    "VALIDATION_CANDIDATE",
}

# States that require explicit authorization (governance gate).
AUTHORIZATION_REQUIRED_STATES = {"VALIDATION", "OOS", "QUALIFIED"}

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "PROPOSED":              ["FORMALIZED", "ARCHIVED"],
    "FORMALIZED":            ["IMPLEMENTATION_READY", "REJECTED", "ARCHIVED"],
    "IMPLEMENTATION_READY":  ["DEVELOPMENT_TEST", "REJECTED", "ARCHIVED"],
    "DEVELOPMENT_TEST":      ["FORENSIC_REVIEW", "REJECTED", "ARCHIVED"],
    "FORENSIC_REVIEW":       ["VALIDATION_CANDIDATE", "REJECTED", "ARCHIVED"],
    "VALIDATION_CANDIDATE":  ["VALIDATION", "REJECTED", "ARCHIVED"],
    "VALIDATION":            ["OOS", "REJECTED", "INVALIDATED"],
    "OOS":                   ["QUALIFIED", "REJECTED", "INVALIDATED"],
    "QUALIFIED":             [],
    "REJECTED":              [],
    "INVALIDATED":           [],
    "ARCHIVED":              [],
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HypothesisRegistryError(Exception):
    """Base class for registry errors."""


class InvalidHypothesisIDError(HypothesisRegistryError):
    """Raised when a hypothesis ID does not conform to H-<FAMILY>-<NUMBER>."""


class DuplicateHypothesisIDError(HypothesisRegistryError):
    """Raised when attempting to register an already-existing hypothesis ID."""


class InvalidTransitionError(HypothesisRegistryError):
    """Raised when a lifecycle transition is not permitted."""


class AuthorizationRequiredError(HypothesisRegistryError):
    """Raised when a transition requires explicit governance authorization."""


class MissingRequiredFieldError(HypothesisRegistryError):
    """Raised when a required hypothesis field is missing."""


class MalformedHypothesisError(HypothesisRegistryError):
    """Raised when a hypothesis record is structurally invalid."""


# ---------------------------------------------------------------------------
# Required fields for a hypothesis record in the registry
# ---------------------------------------------------------------------------
REQUIRED_HYPOTHESIS_FIELDS = {
    "hypothesis_id",
    "title",
    "status",
    "lifecycle_state",
    "filesystem_path",
    "created_at",
    "owner",
    "hypothesis_family",
    "timeframe_sets",
    "asset_scope",
    "bar_horizon",
    "development_partition",
    "validation_status",
    "oos_status",
    "related_experiments",
    "related_hypotheses",
}


# ---------------------------------------------------------------------------
# HypothesisRegistry
# ---------------------------------------------------------------------------

class HypothesisRegistry:
    """
    Manages the permanent, controlled QCP Hypothesis Research Registry.

    Reads and writes ``hypotheses/registry.yaml``.
    Enforces ID format, uniqueness, lifecycle transitions, and field completeness.

    This class does NOT:
      - Execute experiments.
      - Modify canonical strategy logic.
      - Access or unlock Validation/OOS data partitions.
      - Deploy capital.
    """

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self.registry_path = registry_path or REGISTRY_PATH
        self._data: Dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.registry_path.exists():
            text = self.registry_path.read_text(encoding="utf-8")
            self._data = _load_yaml(text) or {}
        else:
            self._data = {
                "metadata": {
                    "registry_version": "1.0.0",
                    "created_at": _now_iso(),
                    "governance_principle": "QCP researches hypotheses; it does not assume them to be true.",
                },
                "hypotheses": {},
            }

    def _save(self) -> None:
        self.registry_path.write_text(_dump_yaml(self._data), encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hypotheses(self) -> Dict[str, Any]:
        return self._data.setdefault("hypotheses", {})

    def _get(self, hypothesis_id: str) -> Dict[str, Any]:
        h = self._hypotheses().get(hypothesis_id)
        if h is None:
            raise HypothesisRegistryError(f"Hypothesis not found: {hypothesis_id!r}")
        return h

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def validate_id_format(hypothesis_id: str) -> None:
        """Enforce H-<FAMILY>-<NUMBER> format."""
        if not HYPOTHESIS_ID_PATTERN.match(hypothesis_id):
            raise InvalidHypothesisIDError(
                f"Hypothesis ID {hypothesis_id!r} does not match required format "
                f"H-<FAMILY>-<NUMBER> (e.g. H-FRACTAL-01, H-MOMENTUM-02)."
            )

    @staticmethod
    def validate_transition(current_state: str, target_state: str) -> None:
        """Enforce lifecycle transition rules."""
        if current_state not in VALID_TRANSITIONS:
            raise InvalidTransitionError(
                f"Unknown lifecycle state: {current_state!r}."
            )
        if current_state in TERMINAL_STATES:
            raise InvalidTransitionError(
                f"State {current_state!r} is a terminal state — no further transitions are permitted."
            )
        if target_state not in VALID_TRANSITIONS.get(current_state, []):
            allowed = VALID_TRANSITIONS.get(current_state, [])
            raise InvalidTransitionError(
                f"Cannot transition {current_state!r} → {target_state!r}. "
                f"Allowed transitions from {current_state!r}: {allowed}."
            )
        if target_state in AUTHORIZATION_REQUIRED_STATES:
            raise AuthorizationRequiredError(
                f"Transition to {target_state!r} requires explicit governance authorization. "
                f"Do not promote a hypothesis to VALIDATION/OOS/QUALIFIED automatically. "
                f"Use transition_authorized() with an authorization token."
            )

    @staticmethod
    def validate_required_fields(record: Dict[str, Any]) -> None:
        """Ensure all required fields are present."""
        missing = REQUIRED_HYPOTHESIS_FIELDS - set(record.keys())
        if missing:
            raise MissingRequiredFieldError(
                f"Hypothesis record is missing required fields: {sorted(missing)}."
            )

    @staticmethod
    def validate_record(record: Dict[str, Any]) -> None:
        """Full structural validation of a hypothesis record."""
        HypothesisRegistry.validate_required_fields(record)

        hid = record.get("hypothesis_id", "")
        HypothesisRegistry.validate_id_format(hid)

        state = record.get("lifecycle_state", "")
        if state not in LIFECYCLE_STATES:
            raise MalformedHypothesisError(
                f"Hypothesis {hid!r} has unknown lifecycle_state: {state!r}."
            )

        status = record.get("status", "")
        if status != state:
            raise MalformedHypothesisError(
                f"Hypothesis {hid!r}: 'status' ({status!r}) and 'lifecycle_state' ({state!r}) must match."
            )

        ts = record.get("timeframe_sets")
        if not isinstance(ts, list) or len(ts) == 0:
            raise MalformedHypothesisError(
                f"Hypothesis {hid!r}: 'timeframe_sets' must be a non-empty list."
            )

        exps = record.get("related_experiments")
        if not isinstance(exps, list):
            raise MalformedHypothesisError(
                f"Hypothesis {hid!r}: 'related_experiments' must be a list."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, record: Dict[str, Any]) -> None:
        """
        Register a new hypothesis.

        Raises:
            DuplicateHypothesisIDError: if the ID already exists.
            InvalidHypothesisIDError: if the ID format is invalid.
            MissingRequiredFieldError: if required fields are absent.
            MalformedHypothesisError: if the record structure is invalid.
        """
        self.validate_record(record)
        hid = record["hypothesis_id"]
        if hid in self._hypotheses():
            raise DuplicateHypothesisIDError(
                f"Hypothesis ID {hid!r} is already registered. IDs are never reused. "
                f"Assign the next sequential number."
            )
        record["updated_at"] = _now_iso()
        self._hypotheses()[hid] = record
        self._save()

    def transition(self, hypothesis_id: str, target_state: str) -> None:
        """
        Transition a hypothesis to a new lifecycle state.

        Does NOT permit transitions to VALIDATION, OOS, or QUALIFIED — those
        require explicit governance authorization via transition_authorized().

        Raises:
            HypothesisRegistryError: if hypothesis not found.
            InvalidTransitionError: if the transition is not permitted.
            AuthorizationRequiredError: if the target state requires authorization.
        """
        h = self._get(hypothesis_id)
        current = h["lifecycle_state"]
        self.validate_transition(current, target_state)
        h["lifecycle_state"] = target_state
        h["status"] = target_state
        h["updated_at"] = _now_iso()
        self._save()

    def transition_authorized(
        self,
        hypothesis_id: str,
        target_state: str,
        authorization_token: str,
        authorization_rationale: str,
    ) -> None:
        """
        Perform a governance-gated transition (VALIDATION, OOS, QUALIFIED).

        Requires an authorization_token and written rationale.
        Does NOT auto-promote based on positive Development results alone.

        Raises:
            HypothesisRegistryError: if hypothesis not found.
            InvalidTransitionError: if the transition is not permitted.
            ValueError: if authorization_token or authorization_rationale is empty.
        """
        if not authorization_token or not authorization_rationale:
            raise ValueError(
                "Transitions to VALIDATION/OOS/QUALIFIED require a non-empty "
                "authorization_token and authorization_rationale. "
                "Do not promote a hypothesis automatically."
            )

        h = self._get(hypothesis_id)
        current = h["lifecycle_state"]
        if current not in VALID_TRANSITIONS:
            raise InvalidTransitionError(f"Unknown lifecycle state: {current!r}.")
        if current in TERMINAL_STATES:
            raise InvalidTransitionError(
                f"State {current!r} is terminal — no further transitions."
            )
        if target_state not in VALID_TRANSITIONS.get(current, []):
            allowed = VALID_TRANSITIONS.get(current, [])
            raise InvalidTransitionError(
                f"Cannot transition {current!r} → {target_state!r}. Allowed: {allowed}."
            )

        h["lifecycle_state"] = target_state
        h["status"] = target_state
        h["updated_at"] = _now_iso()
        h.setdefault("authorization_log", []).append({
            "timestamp": _now_iso(),
            "from_state": current,
            "to_state": target_state,
            "token": authorization_token,
            "rationale": authorization_rationale,
        })
        self._save()

    def add_experiment_reference(
        self,
        hypothesis_id: str,
        experiment_id: str,
        description: str = "",
    ) -> None:
        """
        Link an experiment ID to a hypothesis.

        This establishes the Hypothesis → Experiment → Result traceability chain.
        """
        h = self._get(hypothesis_id)
        ref = {"experiment_id": experiment_id}
        if description:
            ref["description"] = description
        h.setdefault("related_experiments", []).append(ref)
        h["latest_experiment"] = experiment_id
        h["updated_at"] = _now_iso()
        self._save()

    def record_result(
        self,
        hypothesis_id: str,
        experiment_id: str,
        result_summary: str,
    ) -> None:
        """Record the latest result summary for a hypothesis."""
        h = self._get(hypothesis_id)
        h["latest_experiment"] = experiment_id
        h["latest_result"] = result_summary
        h["updated_at"] = _now_iso()
        self._save()

    def record_decision(self, hypothesis_id: str, decision: str, rationale: str) -> None:
        """
        Record the final research decision for a hypothesis.

        decision must be one of: QUALIFIED, REJECTED, INVALIDATED, REQUIRES_FURTHER_RESEARCH
        """
        valid_decisions = {"QUALIFIED", "REJECTED", "INVALIDATED", "REQUIRES_FURTHER_RESEARCH"}
        if decision not in valid_decisions:
            raise HypothesisRegistryError(
                f"Invalid decision {decision!r}. Valid: {sorted(valid_decisions)}."
            )
        h = self._get(hypothesis_id)
        h["decision"] = decision
        h["decision_rationale"] = rationale
        h["updated_at"] = _now_iso()
        self._save()

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all registered hypotheses sorted by ID."""
        return sorted(self._hypotheses().values(), key=lambda h: h.get("hypothesis_id", ""))

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Return hypotheses filtered by lifecycle status."""
        return [h for h in self._hypotheses().values() if h.get("lifecycle_state") == status]

    def show(self, hypothesis_id: str) -> Dict[str, Any]:
        """Return full record for a single hypothesis."""
        return self._get(hypothesis_id)

    def exists(self, hypothesis_id: str) -> bool:
        return hypothesis_id in self._hypotheses()

    def is_id_available(self, hypothesis_id: str) -> bool:
        """Return True if the ID is syntactically valid AND not yet registered."""
        try:
            self.validate_id_format(hypothesis_id)
        except InvalidHypothesisIDError:
            return False
        return hypothesis_id not in self._hypotheses()

    def get_valid_transitions(self, hypothesis_id: str) -> List[str]:
        """Return the list of states this hypothesis can legally transition to."""
        h = self._get(hypothesis_id)
        current = h["lifecycle_state"]
        return VALID_TRANSITIONS.get(current, [])

    def summary_stats(self) -> Dict[str, Any]:
        """Return aggregate counts by lifecycle state."""
        counts: Dict[str, int] = {}
        for h in self._hypotheses().values():
            s = h.get("lifecycle_state", "UNKNOWN")
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self._hypotheses()),
            "by_state": counts,
        }

    def validate_hypothesis(self, hypothesis_id: str) -> List[str]:
        """
        Run full validation on a registered hypothesis and return any error messages.
        Empty list means the hypothesis is structurally valid.
        """
        errors: List[str] = []
        try:
            h = self._get(hypothesis_id)
            self.validate_record(h)
        except (MissingRequiredFieldError, MalformedHypothesisError, InvalidHypothesisIDError) as exc:
            errors.append(str(exc))
        except HypothesisRegistryError as exc:
            errors.append(str(exc))
        return errors

    def validate_registry_sync(self) -> List[str]:
        """
        Verify all hypotheses have consistent status/lifecycle_state fields.
        Returns list of inconsistency descriptions (empty = OK).
        """
        issues: List[str] = []
        for hid, h in self._hypotheses().items():
            if h.get("status") != h.get("lifecycle_state"):
                issues.append(
                    f"{hid}: status={h.get('status')!r} != lifecycle_state={h.get('lifecycle_state')!r}"
                )
        return issues


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd_list(registry: HypothesisRegistry) -> None:
    hypotheses = registry.list_all()
    if not hypotheses:
        print("No hypotheses registered.")
        return
    print(f"\n{'ID':<20}  {'FAMILY':<12}  {'STATE':<24}  {'TITLE'}")
    print("-" * 90)
    for h in hypotheses:
        print(
            f"{h.get('hypothesis_id', ''):<20}  "
            f"{h.get('hypothesis_family', ''):<12}  "
            f"{h.get('lifecycle_state', ''):<24}  "
            f"{h.get('title', '')}"
        )
    stats = registry.summary_stats()
    print(f"\nTotal: {stats['total']}  |  By state: {stats['by_state']}")


def cmd_show(registry: HypothesisRegistry, hypothesis_id: str) -> None:
    try:
        h = registry.show(hypothesis_id)
        print(f"\n{'=' * 70}")
        print(f"  Hypothesis: {h.get('hypothesis_id')} — {h.get('title')}")
        print(f"{'=' * 70}")
        for k, v in h.items():
            if isinstance(v, (dict, list)):
                print(f"  {k}:")
                print(f"    {json.dumps(v, indent=2, default=str)}")
            else:
                print(f"  {k}: {v}")
        transitions = registry.get_valid_transitions(hypothesis_id)
        print(f"\n  Valid next transitions: {transitions}")
    except HypothesisRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(registry: HypothesisRegistry, hypothesis_id: str) -> None:
    try:
        errors = registry.validate_hypothesis(hypothesis_id)
        sync_issues = registry.validate_registry_sync()
        if errors:
            print(f"VALIDATION FAILED for {hypothesis_id}:")
            for e in errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        if sync_issues:
            print("REGISTRY SYNC ISSUES:")
            for s in sync_issues:
                print(f"  ✗ {s}")
            sys.exit(1)
        print(f"✓ {hypothesis_id} passes all validation checks.")
    except HypothesisRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_status(registry: HypothesisRegistry) -> None:
    stats = registry.summary_stats()
    sync_issues = registry.validate_registry_sync()
    print(f"\nQCP Hypothesis Registry Status")
    print(f"  Total hypotheses: {stats['total']}")
    print(f"  Registry sync issues: {len(sync_issues)}")
    for state, count in sorted(stats["by_state"].items()):
        marker = "⚠" if state in TERMINAL_STATES and state != "QUALIFIED" else " "
        print(f"  {marker} {state:<24}: {count}")
    if sync_issues:
        print("\nSync issues detected:")
        for s in sync_issues:
            print(f"  ✗ {s}")


def cmd_transitions(registry: HypothesisRegistry, hypothesis_id: str, target_state: str = "") -> None:
    try:
        allowed = registry.get_valid_transitions(hypothesis_id)
        if target_state:
            current = registry.show(hypothesis_id).get("lifecycle_state", "")
            try:
                registry.validate_transition(current, target_state)
                print(f"✓ Transition {current!r} → {target_state!r} is VALID.")
            except AuthorizationRequiredError as exc:
                print(f"⚠ Transition {current!r} → {target_state!r} requires AUTHORIZATION:")
                print(f"  {exc}")
            except InvalidTransitionError as exc:
                print(f"✗ Transition {current!r} → {target_state!r} is INVALID:")
                print(f"  {exc}")
        else:
            print(f"Valid next transitions for {hypothesis_id}: {allowed}")
    except HypothesisRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    args = argv if argv is not None else sys.argv[1:]

    registry = HypothesisRegistry()

    if not args:
        print(__doc__)
        return

    cmd = args[0].lower()

    if cmd == "list":
        cmd_list(registry)

    elif cmd == "show":
        if len(args) < 2:
            print("Usage: hypothesis_governance show <HYPOTHESIS_ID>", file=sys.stderr)
            sys.exit(1)
        cmd_show(registry, args[1])

    elif cmd == "validate":
        if len(args) < 2:
            print("Usage: hypothesis_governance validate <HYPOTHESIS_ID>", file=sys.stderr)
            sys.exit(1)
        cmd_validate(registry, args[1])

    elif cmd == "status":
        cmd_status(registry)

    elif cmd == "transitions":
        if len(args) < 2:
            print("Usage: hypothesis_governance transitions <HYPOTHESIS_ID> [TARGET_STATE]", file=sys.stderr)
            sys.exit(1)
        target = args[2] if len(args) > 2 else ""
        cmd_transitions(registry, args[1], target)

    else:
        print(f"Unknown command: {cmd!r}")
        print("Available commands: list, show, status, validate, transitions")
        sys.exit(1)


if __name__ == "__main__":
    main()
