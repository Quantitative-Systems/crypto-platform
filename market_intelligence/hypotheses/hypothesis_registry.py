"""Hypothesis Registry: Versioned Empirical Hypothesis Repository & Lifecycle.

Formalizes discovered causal relationships and transmission hypotheses with strict
out-of-sample validation gates and automated lifecycle status management.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class HypothesisStatus(str, Enum):
    CANDIDATE = "CANDIDATE"              # Formulated by research or AI; unverified
    BACKTEST_PASSED = "BACKTEST_PASSED"  # Passed initial backtest
    ACTIVE = "ACTIVE"                    # Fully certified through DEV/VAL/OOS; live in decision engine
    DRIFT_WARNING = "DRIFT_WARNING"      # Realized performance diverging from expected
    SUSPENDED = "SUSPENDED"              # Temporarily disabled due to concept drift; requires re-research
    RETIRED = "RETIRED"                  # Falsified or permanently degraded


class ValidationVerdict(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class CausalHypothesis:
    """Rigorous empirical specification of a causal market relationship."""
    hypothesis_id: str
    name: str
    observation: str
    mechanism: str
    affected_assets: List[str]
    regime_conditions: Dict[str, Any]
    expected_effect: str
    expected_expectancy_r: float = 1.0
    expected_win_rate: float = 0.55
    realized_expectancy_r: float = 0.0
    realized_win_rate: float = 0.0
    evidence_count: int = 0
    dev_verdict: ValidationVerdict = ValidationVerdict.PENDING
    val_verdict: ValidationVerdict = ValidationVerdict.PENDING
    oos_verdict: ValidationVerdict = ValidationVerdict.PENDING
    confidence_score: float = 0.50
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: Dict[str, Any] = field(default_factory=dict)

    def is_fully_validated(self) -> bool:
        """Strict certification invariant: Must PASS DEV, VAL, and OOS."""
        return (
            self.dev_verdict == ValidationVerdict.PASS
            and self.val_verdict == ValidationVerdict.PASS
            and self.oos_verdict == ValidationVerdict.PASS
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "name": self.name,
            "observation": self.observation,
            "mechanism": self.mechanism,
            "affected_assets": self.affected_assets,
            "regime_conditions": self.regime_conditions,
            "expected_effect": self.expected_effect,
            "expected_expectancy_r": self.expected_expectancy_r,
            "expected_win_rate": self.expected_win_rate,
            "realized_expectancy_r": self.realized_expectancy_r,
            "realized_win_rate": self.realized_win_rate,
            "evidence_count": self.evidence_count,
            "dev_verdict": self.dev_verdict.value,
            "val_verdict": self.val_verdict.value,
            "oos_verdict": self.oos_verdict.value,
            "confidence_score": self.confidence_score,
            "status": self.status.value,
            "created_at_utc": self.created_at_utc,
            "last_updated_utc": self.last_updated_utc,
            "meta": self.meta,
        }


class HypothesisRegistry:
    """Repository for managing, verifying, and retiring causal hypotheses."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file
        self.hypotheses: Dict[str, CausalHypothesis] = {}

    def register(self, hypothesis: CausalHypothesis) -> CausalHypothesis:
        """Register or update a hypothesis."""
        hypothesis.last_updated_utc = datetime.now(timezone.utc).isoformat()
        self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        if self.registry_file:
            self.save_to_file()
        return hypothesis

    def get(self, hypothesis_id: str) -> Optional[CausalHypothesis]:
        return self.hypotheses.get(hypothesis_id)

    def get_active_hypotheses(self, asset: Optional[str] = None) -> List[CausalHypothesis]:
        """Retrieve active certified hypotheses matching an asset."""
        return [
            h for h in self.hypotheses.values()
            if h.status == HypothesisStatus.ACTIVE
            and (not asset or asset in h.affected_assets or "ALL" in h.affected_assets)
        ]

    def promote_to_active(self, hypothesis_id: str) -> bool:
        """Promote a hypothesis to ACTIVE if DEV, VAL, and OOS pass."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            return False
        if hyp.is_fully_validated():
            hyp.status = HypothesisStatus.ACTIVE
            hyp.last_updated_utc = datetime.now(timezone.utc).isoformat()
            if self.registry_file:
                self.save_to_file()
            return True
        return False

    def suspend_hypothesis(self, hypothesis_id: str, reason: str = "") -> bool:
        """Suspend an underperforming or drifted hypothesis."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            return False
        hyp.status = HypothesisStatus.SUSPENDED
        hyp.meta["suspension_reason"] = reason
        hyp.last_updated_utc = datetime.now(timezone.utc).isoformat()
        if self.registry_file:
            self.save_to_file()
        return True

    def save_to_file(self) -> None:
        """Serialize registry to disk."""
        if not self.registry_file:
            return
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {h_id: h.to_dict() for h_id, h in self.hypotheses.items()}
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_from_file(self) -> int:
        """Load registered hypotheses from disk."""
        if not self.registry_file or not self.registry_file.exists():
            return 0
        with open(self.registry_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        count = 0
        for h_id, d in payload.items():
            hyp = CausalHypothesis(
                hypothesis_id=d["hypothesis_id"],
                name=d["name"],
                observation=d["observation"],
                mechanism=d["mechanism"],
                affected_assets=d["affected_assets"],
                regime_conditions=d["regime_conditions"],
                expected_effect=d["expected_effect"],
                expected_expectancy_r=d.get("expected_expectancy_r", 1.0),
                expected_win_rate=d.get("expected_win_rate", 0.55),
                realized_expectancy_r=d.get("realized_expectancy_r", 0.0),
                realized_win_rate=d.get("realized_win_rate", 0.0),
                evidence_count=d.get("evidence_count", 0),
                dev_verdict=ValidationVerdict(d.get("dev_verdict", "PENDING")),
                val_verdict=ValidationVerdict(d.get("val_verdict", "PENDING")),
                oos_verdict=ValidationVerdict(d.get("oos_verdict", "PENDING")),
                confidence_score=d.get("confidence_score", 0.5),
                status=HypothesisStatus(d.get("status", "CANDIDATE")),
                created_at_utc=d.get("created_at_utc", ""),
                last_updated_utc=d.get("last_updated_utc", ""),
                meta=d.get("meta", {}),
            )
            self.hypotheses[h_id] = hyp
            count += 1
        return count
