"""STRATA — Formal Strategy Evidence Lifecycle & State Machine.

Enforces the non-negotiable 16-stage strategy maturation lifecycle:
DRAFT → FORMALIZED → BACKTEST → FALSIFICATION → OOS → ADVERSARIAL → ROBUSTNESS →
PAPER → FORWARD → QUALIFICATION → DEPLOYABLE → MONITORED → DEGRADED → QUARANTINED →
RESEARCH → REPLACEMENT.

No strategy can jump stages or be deployed live without qualification.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LifecycleStage(str, Enum):
    DRAFT = "DRAFT"
    FORMALIZED = "FORMALIZED"
    BACKTEST = "BACKTEST"
    FALSIFICATION = "FALSIFICATION"
    OOS = "OOS"
    ADVERSARIAL = "ADVERSARIAL"
    ROBUSTNESS = "ROBUSTNESS"
    PAPER = "PAPER"
    FORWARD = "FORWARD"
    QUALIFICATION = "QUALIFICATION"
    DEPLOYABLE = "DEPLOYABLE"
    MONITORED = "MONITORED"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    RESEARCH = "RESEARCH"
    REPLACEMENT = "REPLACEMENT"


class StrategyVerdict(str, Enum):
    NOT_READY = "NOT_READY"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"
    FORWARD_VALIDATION_ELIGIBLE = "FORWARD_VALIDATION_ELIGIBLE"
    QUALIFIED = "QUALIFIED"


LIFECYCLE_ORDER: List[LifecycleStage] = [
    LifecycleStage.DRAFT,
    LifecycleStage.FORMALIZED,
    LifecycleStage.BACKTEST,
    LifecycleStage.FALSIFICATION,
    LifecycleStage.OOS,
    LifecycleStage.ADVERSARIAL,
    LifecycleStage.ROBUSTNESS,
    LifecycleStage.PAPER,
    LifecycleStage.FORWARD,
    LifecycleStage.QUALIFICATION,
    LifecycleStage.DEPLOYABLE,
    LifecycleStage.MONITORED,
    LifecycleStage.DEGRADED,
    LifecycleStage.QUARANTINED,
    LifecycleStage.RESEARCH,
    LifecycleStage.REPLACEMENT,
]


@dataclass
class StrategyEvidence:
    current_stage: LifecycleStage = LifecycleStage.DRAFT
    verdict: StrategyVerdict = StrategyVerdict.NOT_READY
    total_trades: int = 0
    net_r: float = 0.0
    expectancy_r: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    max_drawdown_r: float = 0.0
    tail_risk_cvar: float = 0.0
    friction_multiplier_survival: float = 1.0
    oos_expectancy_r: float = 0.0
    parameter_stability_score: float = 0.0
    evidence_notes: List[str] = field(default_factory=list)
    last_evaluated_ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["current_stage"] = self.current_stage.value
        d["verdict"] = self.verdict.value
        return d


class LifecycleTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted."""
    pass


class StrategyLifecycleManager:
    """Manages stage transitions and evidence qualification gates."""

    @staticmethod
    def transition(
        evidence: StrategyEvidence,
        target_stage: LifecycleStage,
        note: str = "",
    ) -> StrategyEvidence:
        """Validates and applies lifecycle stage progression."""
        current = evidence.current_stage

        # Allowed transitions
        if target_stage == LifecycleStage.QUARANTINED:
            # Any stage can be quarantined if degraded or invalid
            evidence.current_stage = LifecycleStage.QUARANTINED
            evidence.verdict = StrategyVerdict.NOT_READY
            evidence.evidence_notes.append(f"QUARANTINED: {note}")
            evidence.last_evaluated_ts = time.time()
            return evidence

        curr_idx = LIFECYCLE_ORDER.index(current)
        target_idx = LIFECYCLE_ORDER.index(target_stage)

        # Disallow skipping forward more than 1 stage
        if target_idx > curr_idx + 1:
            raise LifecycleTransitionError(
                f"Cannot skip lifecycle stages: attempted {current.value} -> {target_stage.value}. "
                f"Strategies must progress sequentially through testing gates."
            )

        evidence.current_stage = target_stage
        if note:
            evidence.evidence_notes.append(f"Transitioned to {target_stage.value}: {note}")
        evidence.last_evaluated_ts = time.time()
        return evidence
