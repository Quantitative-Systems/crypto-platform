"""
Product 04 — Research Laboratory: Experiment Schema
Codifies formal schemas for Hypotheses, Experiment Protocols, Falsification Criteria, and Experiment Results.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
import time


@dataclass
class HypothesisSpec:
    """
    Formal specification of a trading hypothesis to be empirically tested.
    """
    hypothesis_id: str
    hypothesis_name: str
    mechanism_description: str
    baseline_id: str = "BASELINE_UNIFIED_V1"
    variable_under_test: str = ""
    control_invariants: List[str] = field(default_factory=lambda: [
        "MAX_RISK_FRACTION_1_PCT",
        "MIN_RR_FLOOR_4_0R",
        "MIN_STOP_DISTANCE_0_10_PCT",
        "MONOTONIC_MTF_STRUCTURAL_TRAILING",
        "ZERO_LOOKAHEAD_CAUSALITY"
    ])
    target_universe: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    timeframe_sets: List[str] = field(default_factory=lambda: ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"])
    sample_period_start: str = "2023-01-01 00:00:00 UTC"
    sample_period_end: str = "2024-01-01 00:00:00 UTC"
    falsification_criteria: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentResult:
    """
    Result of an empirical A/B experiment comparing a treatment hypothesis against a baseline.
    """
    experiment_id: str
    hypothesis_id: str
    baseline_id: str
    variable_under_test: str
    timestamp_utc: str
    status: str  # COMPLETED, FAILED, INCONCLUSIVE
    decision: str  # REJECTED, SURVIVES_FOR_OOS, INCONCLUSIVE
    decision_reasoning: str
    baseline_metrics: Dict[str, Any]
    treatment_metrics: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    stream_level_comparison: List[Dict[str, Any]] = field(default_factory=list)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
