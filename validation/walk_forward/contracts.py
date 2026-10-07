"""Phase K: Walk-Forward Integrated System Validation Contracts.

Domain contracts for evaluating the complete, fully frozen institutional architecture:
Market Model -> Causal Context -> Adaptive Selection -> 7-Layer Governor -> Staged Reactivation -> Position Trail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WalkForwardPartitionType(str, Enum):
    """Chronological dataset partition classification."""
    TRAIN_DEV = "TRAIN_DEV"        # In-sample discovery & model specification
    VALIDATION = "VALIDATION"      # Intermediate structural tuning / calibration verification
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"# Pure unseen future period
    WALK_FORWARD_TEST = "WALK_FORWARD_TEST" # Rolling forward test slice


@dataclass
class WalkForwardFoldSpec:
    """Specification of an anchored/rolling walk-forward fold."""
    fold_index: int
    fold_name: str
    train_start_ts: int
    train_end_ts: int
    test_start_ts: int
    test_end_ts: int
    train_label: str
    test_label: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "fold_name": self.fold_name,
            "train_start_ts": self.train_start_ts,
            "train_end_ts": self.train_end_ts,
            "test_start_ts": self.test_start_ts,
            "test_end_ts": self.test_end_ts,
            "train_label": self.train_label,
            "test_label": self.test_label,
            "description": self.description,
        }


@dataclass
class SystemIntegrityCheckRecord:
    """Rigorous pre-flight & runtime causality audit record."""
    check_name: str
    passed: bool
    violations_count: int
    total_samples_audited: int
    details: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "violations_count": self.violations_count,
            "total_samples_audited": self.total_samples_audited,
            "details": self.details,
            "meta": self.meta,
        }


@dataclass
class FoldPerformanceMetrics:
    """Performance evaluation of a system architecture within a walk-forward fold."""
    fold_index: int
    fold_name: str
    partition_type: WalkForwardPartitionType
    system_id: str
    system_name: str
    trade_count: int
    net_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    var_95_r: float
    cvar_95_r: float
    fees_and_slippage_r: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "fold_name": self.fold_name,
            "partition_type": self.partition_type.value,
            "system_id": self.system_id,
            "system_name": self.system_name,
            "trade_count": self.trade_count,
            "net_r": self.net_r,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "var_95_r": self.var_95_r,
            "cvar_95_r": self.cvar_95_r,
            "fees_and_slippage_r": self.fees_and_slippage_r,
            "meta": self.meta,
        }


@dataclass
class IntegratedSystemValidationReport:
    """Master institutional report across all 4 core validation dimensions."""
    timestamp_utc: str
    phase: str = "PHASE_K_WALK_FORWARD_INTEGRATED_VALIDATION"
    alpha_preservation_score: float = 0.0     # OOS Net R / In-Sample Net R ratio
    defensive_efficiency_score: float = 0.0   # OOS Max DD reduction %
    recovery_efficacy_score: float = 0.0      # Post-crisis recovery R capture %
    integrity_audit_passed: bool = True       # Zero lookahead, zero data leakage
    integrity_checks: List[SystemIntegrityCheckRecord] = field(default_factory=list)
    fold_metrics: List[FoldPerformanceMetrics] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "phase": self.phase,
            "alpha_preservation_score": self.alpha_preservation_score,
            "defensive_efficiency_score": self.defensive_efficiency_score,
            "recovery_efficacy_score": self.recovery_efficacy_score,
            "integrity_audit_passed": self.integrity_audit_passed,
            "integrity_checks": [c.to_dict() for c in self.integrity_checks],
            "fold_metrics": [m.to_dict() for m in self.fold_metrics],
            "summary": self.summary,
        }
