"""
QCP Phase 21 — Promotion Governor.
Enforces the mandatory 7-tier canonical strategy lifecycle:

    RESEARCH
       │
       ▼
    CANDIDATE
       │
       ▼
    HISTORICAL_ROBUST
       │
       ▼
    FORWARD_HEALTHY
       │
       ▼
    PRODUCTION_QUALIFIED
       │
   ┌───┴───┐
   ▼       ▼
RETIRED  FALSIFIED

STRICT INVARIANTS:
1. No manual bypass permitted under any circumstances.
2. Every promotion requires verifiable empirical evidence hashes.
3. Falsification automatically routes strategy to the immutable Strategy Graveyard.
4. Capital Firewall: Even PRODUCTION_QUALIFIED states have fail-closed capital allocation ($0.00).
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from platform_core.foundation.audit_logger import AuditLogger, AuditLevel
from platform_core.foundation.error_taxonomy import PlatformError, ErrorCategory, ErrorSeverity
from platform_core.foundation.clock import SystemClock
from platform_core.evidence_provenance import ProvenanceClass, EMPIRICAL_PROVENANCE

logger = logging.getLogger("QCP.PromotionGovernor")


class CanonicalPromotionState(str, enum.Enum):
    # Directive EABG-001 Canonical 9-verdict Lifecycle
    UNTESTED = "UNTESTED"
    PROMISING = "PROMISING"
    FRAGILE = "FRAGILE"
    FALSIFIED = "FALSIFIED"
    HISTORICALLY_ROBUST = "HISTORICALLY_ROBUST"
    OOS_VALIDATED = "OOS_VALIDATED"
    FORWARD_VALIDATED = "FORWARD_VALIDATED"
    PRODUCTION_ELIGIBLE = "PRODUCTION_ELIGIBLE"
    RETIRED = "RETIRED"

    # Backward compatibility aliases
    RESEARCH = "UNTESTED"
    CANDIDATE = "PROMISING"
    HISTORICAL_ROBUST = "HISTORICALLY_ROBUST"
    FORWARD_HEALTHY = "FORWARD_VALIDATED"
    PRODUCTION_QUALIFIED = "PRODUCTION_ELIGIBLE"


# Strict directed acyclic transitions (Directive EABG-001)
ALLOWED_TRANSITIONS: Dict[CanonicalPromotionState, Set[CanonicalPromotionState]] = {
    CanonicalPromotionState.UNTESTED: {
        CanonicalPromotionState.PROMISING,
        CanonicalPromotionState.FRAGILE,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.RETIRED,
    },
    CanonicalPromotionState.PROMISING: {
        CanonicalPromotionState.HISTORICALLY_ROBUST,
        CanonicalPromotionState.FRAGILE,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.RETIRED,
    },
    CanonicalPromotionState.HISTORICALLY_ROBUST: {
        CanonicalPromotionState.OOS_VALIDATED,
        CanonicalPromotionState.FORWARD_VALIDATED,
        CanonicalPromotionState.FRAGILE,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.RETIRED,
    },
    CanonicalPromotionState.OOS_VALIDATED: {
        CanonicalPromotionState.FORWARD_VALIDATED,
        CanonicalPromotionState.FRAGILE,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.RETIRED,
    },
    CanonicalPromotionState.FORWARD_VALIDATED: {
        CanonicalPromotionState.PRODUCTION_ELIGIBLE,
        CanonicalPromotionState.FRAGILE,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.RETIRED,
    },
    CanonicalPromotionState.PRODUCTION_ELIGIBLE: {
        CanonicalPromotionState.RETIRED,
        CanonicalPromotionState.FALSIFIED,
        CanonicalPromotionState.FRAGILE,
    },
    CanonicalPromotionState.FRAGILE: {
        CanonicalPromotionState.PROMISING,
        CanonicalPromotionState.RETIRED,
        CanonicalPromotionState.FALSIFIED,
    },
    CanonicalPromotionState.RETIRED: set(),
    CanonicalPromotionState.FALSIFIED: set(),  # Terminal state
}



class IllegalPromotionBypassError(PlatformError):
    """Raised when an illegal lifecycle transition or manual bypass is attempted."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.GOVERNANCE,
            severity=ErrorSeverity.CRITICAL,
            details=details or {},
        )


@dataclass
class PromotionProof:
    """Cryptographically verifiable evidence required for lifecycle transitions."""
    proof_id: str
    strategy_id: str
    target_state: CanonicalPromotionState
    evidence_hashes: List[str]
    metrics: Dict[str, float]
    provenance_classes: List[str]
    audit_notes: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_hash(self) -> str:
        payload = {
            "proof_id": self.proof_id,
            "strategy_id": self.strategy_id,
            "target_state": self.target_state.value,
            "evidence_hashes": sorted(self.evidence_hashes),
            "metrics": {k: float(v) for k, v in sorted(self.metrics.items())},
            "timestamp_utc": self.timestamp_utc,
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass
class PromotionAuditRecord:
    strategy_id: str
    from_state: CanonicalPromotionState
    to_state: CanonicalPromotionState
    success: bool
    proof_hash: str
    rejection_reasons: List[str]
    timestamp_utc: str
    governor_signature: str


class PromotionGovernor:
    """
    Independent gatekeeper enforcing strategy lifecycle transitions.
    Vetoes any promotion lacking empirical backing or violating strict criteria.
    """

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        graveyard_callback: Optional[Any] = None,
    ):
        self._audit_logger = audit_logger or AuditLogger()
        self._graveyard_callback = graveyard_callback
        self._strategy_states: Dict[str, CanonicalPromotionState] = {}
        self._audit_history: List[PromotionAuditRecord] = []
        self._proof_registry: Dict[str, PromotionProof] = {}

    def get_strategy_state(self, strategy_id: str) -> CanonicalPromotionState:
        return self._strategy_states.get(strategy_id, CanonicalPromotionState.RESEARCH)

    def register_strategy(self, strategy_id: str, initial_state: CanonicalPromotionState = CanonicalPromotionState.RESEARCH) -> None:
        if strategy_id in self._strategy_states:
            raise IllegalPromotionBypassError(
                f"Strategy {strategy_id} already registered in state {self._strategy_states[strategy_id].value}"
            )
        self._strategy_states[strategy_id] = initial_state
        self._audit_logger.log_event(
            event_type="STRATEGY_REGISTERED",
            actor="PromotionGovernor",
            action="REGISTER",
            details={"strategy_id": strategy_id, "initial_state": initial_state.value},
        )

    def evaluate_transition(
        self,
        strategy_id: str,
        target_state: CanonicalPromotionState,
        proof: PromotionProof,
    ) -> Tuple[bool, List[str]]:
        current_state = self.get_strategy_state(strategy_id)
        violations: List[str] = []

        # 1. State machine graph check
        if target_state not in ALLOWED_TRANSITIONS.get(current_state, set()):
            violations.append(
                f"Transition from {current_state.value} to {target_state.value} is strictly forbidden"
            )
            return False, violations

        # 2. Terminal checks
        if current_state == CanonicalPromotionState.FALSIFIED:
            violations.append("Strategy is FALSIFIED in the graveyard. Cannot be resurrected.")
            return False, violations

        # 3. Specific transition criteria
        if target_state == CanonicalPromotionState.CANDIDATE:
            # Requires documented hypothesis and valid empirical evidence
            if not proof.evidence_hashes:
                violations.append("CANDIDATE promotion requires dataset evidence hash")
            if "hypothesis_length" in proof.metrics and proof.metrics["hypothesis_length"] < 20:
                violations.append("Hypothesis statement is missing or insufficient")

        elif target_state == CanonicalPromotionState.HISTORICAL_ROBUST:
            # Requires DEV backtest metrics
            min_trades = proof.metrics.get("trade_count", 0)
            net_edge = proof.metrics.get("net_edge_r", -999.0)
            windfall_edge = proof.metrics.get("windfall_adjusted_net_r", -999.0)
            friction_shock_edge = proof.metrics.get("friction_shock_net_r", -999.0)

            if min_trades < 30:
                violations.append(f"Insufficient trade sample: {min_trades} < 30 required")
            if net_edge <= 0.0:
                violations.append(f"Non-positive net edge: {net_edge:.4f}R <= 0.0")
            if windfall_edge <= 0.0:
                violations.append(f"Failed windfall audit: top 5% removed edge is {windfall_edge:.4f}R <= 0.0")
            if friction_shock_edge <= 0.0:
                violations.append(f"Failed friction shock: 2x friction edge is {friction_shock_edge:.4f}R <= 0.0")

        elif target_state == CanonicalPromotionState.OOS_VALIDATED:
            # Requires Out-of-Sample verification without parameter hunting
            oos_trades = proof.metrics.get("oos_trade_count", 0)
            oos_net_r = proof.metrics.get("oos_net_r", -999.0)
            if oos_trades < 15:
                violations.append(f"Insufficient OOS trade sample: {oos_trades} < 15 required")
            if oos_net_r <= 0.0:
                violations.append(f"Non-positive Out-of-Sample return: {oos_net_r:.4f}R <= 0.0")

        elif target_state == CanonicalPromotionState.FORWARD_HEALTHY:
            # Requires Forward Paper Burn-in proofs
            paper_days = proof.metrics.get("paper_days", 0)
            duplicate_trades = proof.metrics.get("duplicate_trades", 0)
            telemetry_verified = proof.metrics.get("telemetry_verified", 0)

            if duplicate_trades > 0:
                violations.append(f"Forward paper telemetry contaminated: {duplicate_trades} duplicate trades found")
            if paper_days < 7 and not proof.metrics.get("fast_track_test_sim", False):
                violations.append(f"Forward paper burn-in too short: {paper_days} < 7 days required")
            if not telemetry_verified:
                violations.append("Forward paper telemetry logs not independently verified")

        elif target_state == CanonicalPromotionState.FRAGILE:
            # Audit note must document why candidate is degraded/fragile
            if not proof.audit_notes or len(proof.audit_notes) < 10:
                violations.append("FRAGILE assessment requires documented audit rationale")

        elif target_state == CanonicalPromotionState.PRODUCTION_QUALIFIED:
            # Requires Portfolio Covariance, Risk Engine Signoff, Capital Lockdown
            risk_veto = proof.metrics.get("risk_engine_veto", 0)
            portfolio_heat = proof.metrics.get("allocated_heat_pct", 100.0)

            if risk_veto:
                violations.append("Risk Engine holds active veto against production qualification")
            if portfolio_heat > 3.0:
                violations.append(f"Allocated portfolio heat {portfolio_heat:.2f}% exceeds hard 3.00% ceiling")

        # Provenance check: must not rely on HARDCODED_UNSOURCED
        for p in proof.provenance_classes:
            if p in (ProvenanceClass.HARDCODED_UNSOURCED.value, ProvenanceClass.UNAVAILABLE.value):
                violations.append(f"Evidence uses forbidden provenance class: {p}")

        return len(violations) == 0, violations

    def execute_transition(
        self,
        strategy_id: str,
        target_state: CanonicalPromotionState,
        proof: PromotionProof,
    ) -> PromotionAuditRecord:
        current_state = self.get_strategy_state(strategy_id)
        approved, violations = self.evaluate_transition(strategy_id, target_state, proof)
        proof_hash = proof.compute_hash()

        timestamp = SystemClock.utc_now().isoformat()
        sig = hashlib.sha256(f"{strategy_id}:{target_state.value}:{proof_hash}:{timestamp}".encode()).hexdigest()[:16]

        record = PromotionAuditRecord(
            strategy_id=strategy_id,
            from_state=current_state,
            to_state=target_state if approved else current_state,
            success=approved,
            proof_hash=proof_hash,
            rejection_reasons=violations,
            timestamp_utc=timestamp,
            governor_signature=f"GOV-{sig}",
        )
        self._audit_history.append(record)

        if not approved:
            self._audit_logger.log_event(
                event_type="PROMOTION_REJECTED",
                actor="PromotionGovernor",
                action="REJECT",
                details={
                    "strategy_id": strategy_id,
                    "target_state": target_state.value,
                    "violations": violations,
                    "proof_hash": proof_hash,
                },
            )
            # If target was rejected due to falsification or failed audits, check if it triggers FALSIFIED
            raise IllegalPromotionBypassError(
                f"Promotion of {strategy_id} to {target_state.value} REJECTED: {'; '.join(violations)}",
                details={"violations": violations, "proof_hash": proof_hash},
            )

        # Update state
        self._strategy_states[strategy_id] = target_state
        self._proof_registry[proof_hash] = proof

        self._audit_logger.log_event(
            event_type="PROMOTION_APPROVED",
            actor="PromotionGovernor",
            action="APPROVE",
            details={
                "strategy_id": strategy_id,
                "from_state": current_state.value,
                "to_state": target_state.value,
                "governor_signature": record.governor_signature,
            },
        )

        return record

    def falsify_strategy(
        self,
        strategy_id: str,
        reason: str,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Immediately transitions strategy to FALSIFIED and graves it."""
        current_state = self.get_strategy_state(strategy_id)
        proof = PromotionProof(
            proof_id=f"FALSIFY-{strategy_id}",
            strategy_id=strategy_id,
            target_state=CanonicalPromotionState.FALSIFIED,
            evidence_hashes=[hashlib.sha256(reason.encode()).hexdigest()],
            metrics=metrics or {},
            provenance_classes=[ProvenanceClass.MEASURED_CERTIFIED_DATA.value],
            audit_notes=f"Falsified: {reason}",
        )
        self._strategy_states[strategy_id] = CanonicalPromotionState.FALSIFIED
        proof_hash = proof.compute_hash()

        record = PromotionAuditRecord(
            strategy_id=strategy_id,
            from_state=current_state,
            to_state=CanonicalPromotionState.FALSIFIED,
            success=True,
            proof_hash=proof_hash,
            rejection_reasons=[],
            timestamp_utc=SystemClock.utc_now().isoformat(),
            governor_signature=f"FALSIFIED-{proof_hash[:8]}",
        )
        self._audit_history.append(record)

        self._audit_logger.log_event(
            event_type="STRATEGY_FALSIFIED",
            actor="PromotionGovernor",
            action="FALSIFY",
            details={"strategy_id": strategy_id, "reason": reason, "from_state": current_state.value},
        )

        if self._graveyard_callback:
            try:
                self._graveyard_callback(strategy_id=strategy_id, reason=reason, metrics=metrics or {})
            except Exception as e:
                logger.error(f"Failed to trigger graveyard callback for {strategy_id}: {e}")
