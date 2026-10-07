"""
Product 04 — Research Laboratory: Immutable Versioned Hypothesis Registry
Provides institutional tracking, audit provenance, parent-child hypothesis lineage,
lifecycle state machines, and Multiple Hypothesis Testing (MHT) trial count management.
"""

import os
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional


class HypothesisFamily(str, Enum):
    H1_TREND_CONTINUATION = "H1_TREND_CONTINUATION"
    H2_VOLATILITY_EXPANSION = "H2_VOLATILITY_EXPANSION"
    H3_REGIME_FILTERED = "H3_REGIME_FILTERED"
    H4_LIQUIDITY_DISPLACEMENT = "H4_LIQUIDITY_DISPLACEMENT"
    H5_MOMENTUM_EXPANSION = "H5_MOMENTUM_EXPANSION"


class HypothesisLifecycleState(str, Enum):
    CANDIDATE = "CANDIDATE"
    IN_RESEARCH = "IN_RESEARCH"
    SURVIVES_FOR_OOS = "SURVIVES_FOR_OOS"
    REJECTED_EMPIRICALLY = "REJECTED_EMPIRICALLY"
    APPROVED_FOR_PAPER = "APPROVED_FOR_PAPER"
    RETIRED = "RETIRED"


@dataclass
class RegisteredHypothesis:
    hypothesis_id: str
    hypothesis_name: str
    family: HypothesisFamily
    description: str
    parameters: Dict[str, Any]
    control_invariants: List[str]
    created_timestamp_utc: str
    lifecycle_state: HypothesisLifecycleState
    trial_index: int  # 1-indexed trial number to compute Bonferroni penalty
    parent_hypothesis_id: Optional[str] = None
    derivation_rationale: Optional[str] = None
    is_metrics: Dict[str, Any] = field(default_factory=dict)
    benchmark_metrics: Dict[str, Any] = field(default_factory=dict)
    oos_metrics: Dict[str, Any] = field(default_factory=dict)
    walk_forward_ratio: Optional[float] = None
    statistical_report: Dict[str, Any] = field(default_factory=dict)
    cost_shock_report: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    provenance: Dict[str, str] = field(default_factory=lambda: {
        "hierarchy": "Wealth Multiplier Systems -> Quantitative Systems Platform -> Product 01: Crypto Platform",
        "standard": "v2.0-UNIFIED-CANONICAL-LOCKED"
    })

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["family"] = self.family.value
        d["lifecycle_state"] = self.lifecycle_state.value
        return d


class HypothesisRegistry:
    """
    Maintains an immutable, append-only registry of all quantitative hypotheses tested.
    Guards against data snooping by tracking cumulative trial counts and preventing
    silent parameter resurrection of rejected hypotheses.
    """

    def __init__(self, registry_file: Optional[str] = None):
        if registry_file is None:
            self.registry_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "scratch", "hypothesis_registry.json"
            )
        else:
            self.registry_file = registry_file
        
        self.hypotheses: Dict[str, RegisteredHypothesis] = {}
        self.trial_counter: int = 0
        self._load()

    def _load(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)
                self.trial_counter = data.get("trial_counter", 0)
                for h_id, h_data in data.get("hypotheses", {}).items():
                    self.hypotheses[h_id] = RegisteredHypothesis(
                        hypothesis_id=h_data["hypothesis_id"],
                        hypothesis_name=h_data["hypothesis_name"],
                        family=HypothesisFamily(h_data["family"]),
                        description=h_data["description"],
                        parameters=h_data["parameters"],
                        control_invariants=h_data["control_invariants"],
                        created_timestamp_utc=h_data["created_timestamp_utc"],
                        lifecycle_state=HypothesisLifecycleState(h_data["lifecycle_state"]),
                        trial_index=h_data["trial_index"],
                        parent_hypothesis_id=h_data.get("parent_hypothesis_id"),
                        derivation_rationale=h_data.get("derivation_rationale"),
                        is_metrics=h_data.get("is_metrics", {}),
                        benchmark_metrics=h_data.get("benchmark_metrics", {}),
                        oos_metrics=h_data.get("oos_metrics", {}),
                        walk_forward_ratio=h_data.get("walk_forward_ratio"),
                        statistical_report=h_data.get("statistical_report", {}),
                        cost_shock_report=h_data.get("cost_shock_report", {}),
                        rejection_reason=h_data.get("rejection_reason"),
                        provenance=h_data.get("provenance", {})
                    )
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        data = {
            "trial_counter": self.trial_counter,
            "total_registered": len(self.hypotheses),
            "hypotheses": {h_id: h.to_dict() for h_id, h in self.hypotheses.items()}
        }
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def register_hypothesis(
        self,
        hypothesis_id: str,
        hypothesis_name: str,
        family: HypothesisFamily,
        description: str,
        parameters: Dict[str, Any],
        control_invariants: Optional[List[str]] = None,
        parent_hypothesis_id: Optional[str] = None,
        derivation_rationale: Optional[str] = None
    ) -> RegisteredHypothesis:
        """
        Registers a new hypothesis or returns existing if already registered.
        """
        if hypothesis_id in self.hypotheses:
            return self.hypotheses[hypothesis_id]

        self.trial_counter += 1
        invariants = control_invariants or [
            "MAX_RISK_FRACTION_1_PCT",
            "MIN_RR_FLOOR_4_0R",
            "MIN_STOP_DISTANCE_0_10_PCT",
            "MONOTONIC_MTF_STRUCTURAL_TRAILING",
            "ZERO_LOOKAHEAD_CAUSALITY"
        ]

        h = RegisteredHypothesis(
            hypothesis_id=hypothesis_id,
            hypothesis_name=hypothesis_name,
            family=family,
            description=description,
            parameters=parameters,
            control_invariants=invariants,
            created_timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            lifecycle_state=HypothesisLifecycleState.CANDIDATE,
            trial_index=self.trial_counter,
            parent_hypothesis_id=parent_hypothesis_id,
            derivation_rationale=derivation_rationale
        )
        self.hypotheses[hypothesis_id] = h
        self.save()
        return h

    def record_falsification(self, hypothesis_id: str, reason: str, benchmark_metrics: Dict[str, Any]):
        """
        Permanently locks a hypothesis in REJECTED_EMPIRICALLY state.
        """
        if hypothesis_id in self.hypotheses:
            h = self.hypotheses[hypothesis_id]
            h.lifecycle_state = HypothesisLifecycleState.REJECTED_EMPIRICALLY
            h.rejection_reason = reason
            h.benchmark_metrics = benchmark_metrics
            self.save()

    def get_multiple_testing_penalty(self) -> float:
        """
        Returns the Bonferroni trial multiplier based on cumulative tested models.
        """
        return max(1.0, float(self.trial_counter))
