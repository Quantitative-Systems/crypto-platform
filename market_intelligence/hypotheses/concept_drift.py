"""Concept Drift Detection: Empirical Edge Decay & Distribution Shift Monitoring.

Continuously compares realized trading performance against expected hypothesis statistics,
safely transitioning decaying hypotheses:
NORMAL -> DRIFT_WARNING -> DEGRADATION -> SUSPEND_HYPOTHESIS -> RESEARCH -> REVALIDATE.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from market_intelligence.hypotheses.hypothesis_registry import (
    CausalHypothesis,
    HypothesisRegistry,
    HypothesisStatus,
)


class DriftSeverity(str, Enum):
    NORMAL = "NORMAL"
    DRIFT_WARNING = "DRIFT_WARNING"
    DEGRADATION = "DEGRADATION"
    CRITICAL_FAILURE = "CRITICAL_FAILURE"


@dataclass
class DriftReport:
    """Diagnostic audit of hypothesis performance drift."""
    hypothesis_id: str
    sample_size: int
    expected_expectancy_r: float
    realized_expectancy_r: float
    expectancy_decay_pct: float
    expected_win_rate: float
    realized_win_rate: float
    win_rate_delta: float
    severity: DriftSeverity
    action_taken: str
    recommendation: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "sample_size": self.sample_size,
            "expected_expectancy_r": self.expected_expectancy_r,
            "realized_expectancy_r": self.realized_expectancy_r,
            "expectancy_decay_pct": self.expectancy_decay_pct,
            "expected_win_rate": self.expected_win_rate,
            "realized_win_rate": self.realized_win_rate,
            "win_rate_delta": self.win_rate_delta,
            "severity": self.severity.value,
            "action_taken": self.action_taken,
            "recommendation": self.recommendation,
            "meta": self.meta,
        }


class ConceptDriftDetector:
    """Monitors live and paper execution outcomes against theoretical hypothesis distributions."""

    def __init__(
        self,
        registry: HypothesisRegistry,
        min_sample_size: int = 10,
        warning_decay_pct: float = 35.0,     # Expectancy down > 35%
        degradation_decay_pct: float = 65.0, # Expectancy down > 65%
    ):
        self.registry = registry
        self.min_sample_size = min_sample_size
        self.warning_decay_pct = warning_decay_pct
        self.degradation_decay_pct = degradation_decay_pct

    def monitor_hypothesis(
        self,
        hypothesis_id: str,
        realized_r_outcomes: List[float],
    ) -> DriftReport:
        """Evaluate recent trade results for a specific hypothesis."""
        hyp = self.registry.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis {hypothesis_id} not found in registry.")

        n = len(realized_r_outcomes)
        if n < self.min_sample_size:
            return DriftReport(
                hypothesis_id=hypothesis_id,
                sample_size=n,
                expected_expectancy_r=hyp.expected_expectancy_r,
                realized_expectancy_r=0.0,
                expectancy_decay_pct=0.0,
                expected_win_rate=hyp.expected_win_rate,
                realized_win_rate=0.0,
                win_rate_delta=0.0,
                severity=DriftSeverity.NORMAL,
                action_taken="GATHERING_EVIDENCE",
                recommendation=f"Sample size {n} below minimum threshold {self.min_sample_size}.",
            )

        realized_exp = float(sum(realized_r_outcomes) / n)
        wins = sum(1 for r in realized_r_outcomes if r > 0)
        realized_wr = float(wins / n)

        # Update hypothesis object metrics
        hyp.evidence_count = n
        hyp.realized_expectancy_r = realized_exp
        hyp.realized_win_rate = realized_wr

        # Calculate decay percentage
        exp_decay = 0.0
        if hyp.expected_expectancy_r > 0:
            exp_decay = max(0.0, (hyp.expected_expectancy_r - realized_exp) / hyp.expected_expectancy_r * 100.0)
        elif realized_exp < hyp.expected_expectancy_r:
            exp_decay = 100.0

        wr_delta = realized_wr - hyp.expected_win_rate

        # Determine severity and state transition
        if realized_exp < 0.0 or exp_decay >= self.degradation_decay_pct:
            severity = DriftSeverity.DEGRADATION
            action = "SUSPEND_HYPOTHESIS"
            rec = "Significant edge erosion detected. Suspend from live execution and initiate re-research."
            self.registry.suspend_hypothesis(
                hypothesis_id,
                reason=f"Degradation: realized expectancy {realized_exp:+.2f}R vs expected {hyp.expected_expectancy_r:+.2f}R.",
            )
        elif exp_decay >= self.warning_decay_pct or wr_delta < -0.15:
            severity = DriftSeverity.DRIFT_WARNING
            action = "WARNING_FLAG_SET"
            rec = "Mild performance decay. Maintain active status with haircut position sizing."
            hyp.status = HypothesisStatus.DRIFT_WARNING
        else:
            severity = DriftSeverity.NORMAL
            action = "MAINTAIN_ACTIVE"
            rec = "Performance matches empirical expectations within statistical bounds."
            if hyp.status == HypothesisStatus.DRIFT_WARNING:
                hyp.status = HypothesisStatus.ACTIVE

        return DriftReport(
            hypothesis_id=hypothesis_id,
            sample_size=n,
            expected_expectancy_r=hyp.expected_expectancy_r,
            realized_expectancy_r=realized_exp,
            expectancy_decay_pct=exp_decay,
            expected_win_rate=hyp.expected_win_rate,
            realized_win_rate=realized_wr,
            win_rate_delta=wr_delta,
            severity=severity,
            action_taken=action,
            recommendation=rec,
        )
