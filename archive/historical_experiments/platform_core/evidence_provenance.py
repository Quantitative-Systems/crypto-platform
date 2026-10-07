"""
QCP Evidence Provenance & Promotion Gate.
Institutional truth layer enforcing the platform's non-negotiable law:

    Simulated, modeled, synthetic or unsourced evidence may NEVER be promoted
    to an economic or capital claim.

Every quantitative metric asserted about an alpha must be accompanied by an
EvidenceRecord describing WHERE the number came from. The PromotionGate then
caps the lifecycle state an alpha is allowed to reach based on the WEAKEST
provenance present in its evidence ledger.

This module exists because a research platform that cannot distinguish a
measured number from a typed-in number is not a research platform.
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from platform_core.alpha_genome import AlphaLifecycleState


class ProvenanceClass(str, enum.Enum):
    """
    Ordered from strongest to weakest empirical standing.

    MEASURED_CERTIFIED_DATA    : computed from a certified, checksummed dataset
    MEASURED_UNCERTIFIED_DATA  : computed from real data lacking certification
    MODEL_DERIVED              : produced by a model/simulation
    SYNTHETIC                  : produced from generated (non-market) data
    HARDCODED_UNSOURCED        : a literal constant with no reproducible origin
    UNAVAILABLE                : no evidence exists for this metric
    """

    MEASURED_CERTIFIED_DATA = "MEASURED_CERTIFIED_DATA"
    MEASURED_UNCERTIFIED_DATA = "MEASURED_UNCERTIFIED_DATA"
    MODEL_DERIVED = "MODEL_DERIVED"
    SYNTHETIC = "SYNTHETIC"
    HARDCODED_UNSOURCED = "HARDCODED_UNSOURCED"
    UNAVAILABLE = "UNAVAILABLE"


#: Provenance classes permitted to support an economic net-edge claim.
EMPIRICAL_PROVENANCE: Set[ProvenanceClass] = {
    ProvenanceClass.MEASURED_CERTIFIED_DATA,
    ProvenanceClass.MEASURED_UNCERTIFIED_DATA,
}

#: Performance metrics that must exist, with empirical provenance, before any
#: alpha may be treated as an economic candidate.
REQUIRED_ECONOMIC_METRICS: List[str] = [
    "net_edge_r",
    "gross_edge_r",
    "trade_count",
    "win_rate",
    "profit_factor",
    "max_drawdown_r",
]

#: Metrics that are only meaningful as measured observations; never as inputs.
DERIVED_ONLY_METRICS: List[str] = ["uncertainty_se", "annualized_sharpe", "calmar_ratio"]


@dataclass
class EvidenceRecord:
    """A single, traceable quantitative assertion."""

    metric: str
    value: float
    provenance: ProvenanceClass
    method: str
    source_dataset_id: Optional[str] = None
    source_dataset_sha256: Optional[str] = None
    partition: Optional[str] = None
    alpha_id: Optional[str] = None
    code_version: Optional[str] = None
    reproducible_command: Optional[str] = None
    note: Optional[str] = None
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.value
        return d


@dataclass
class PromotionDecision:
    alpha_id: str
    requested_state: AlphaLifecycleState
    allowed_state: AlphaLifecycleState
    approved: bool
    violations: List[str]
    provenance_summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_id": self.alpha_id,
            "requested_state": self.requested_state.value,
            "allowed_state": self.allowed_state.value,
            "approved": self.approved,
            "violations": self.violations,
            "provenance_summary": self.provenance_summary,
        }


class EvidenceLedger:
    """Ordered collection of evidence records for a single alpha or cycle."""

    def __init__(self, alpha_id: Optional[str] = None):
        self.alpha_id = alpha_id
        self.records: List[EvidenceRecord] = []

    def add(self, record: EvidenceRecord) -> None:
        self.records.append(record)

    def record(
        self,
        metric: str,
        value: float,
        provenance: ProvenanceClass,
        method: str,
        **kwargs: Any,
    ) -> EvidenceRecord:
        rec = EvidenceRecord(
            metric=metric,
            value=float(value),
            provenance=provenance,
            method=method,
            alpha_id=kwargs.pop("alpha_id", self.alpha_id),
            **kwargs,
        )
        self.add(rec)
        return rec

    def metrics(self) -> Dict[str, List[EvidenceRecord]]:
        out: Dict[str, List[EvidenceRecord]] = {}
        for r in self.records:
            out.setdefault(r.metric, []).append(r)
        return out

    def metrics_at(self, partition: str) -> Dict[str, List[EvidenceRecord]]:
        out: Dict[str, List[EvidenceRecord]] = {}
        for r in self.records:
            if r.partition == partition:
                out.setdefault(r.metric, []).append(r)
        return out

    def provenance_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self.records:
            counts[r.provenance.value] = counts.get(r.provenance.value, 0) + 1
        return counts

    def _sorted(self) -> List[ProvenanceClass]:
        order = list(ProvenanceClass)
        return sorted((r.provenance for r in self.records), key=order.index)

    def strongest_provenance(self) -> Optional[ProvenanceClass]:
        ranked = self._sorted()
        return ranked[0] if ranked else None

    def weakest_provenance(self) -> Optional[ProvenanceClass]:
        ranked = self._sorted()
        return ranked[-1] if ranked else None

    def is_empirically_measured(self) -> bool:
        """
        True only when every required economic metric is present with empirical
        provenance. A single synthetic or hard-coded performance metric
        invalidates the entire performance claim.
        """
        by_metric = self.metrics()
        for metric in REQUIRED_ECONOMIC_METRICS:
            records = by_metric.get(metric)
            if not records:
                return False
            if not any(r.provenance in EMPIRICAL_PROVENANCE for r in records):
                return False
        return True

    def has_empirical_evidence(self) -> bool:
        return any(r.provenance in EMPIRICAL_PROVENANCE for r in self.records)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_id": self.alpha_id,
            "record_count": len(self.records),
            "provenance_summary": self.provenance_summary(),
            "is_empirically_measured": self.is_empirically_measured(),
            "records": [r.to_dict() for r in self.records],
        }


class PromotionGate:
    """
    Structural firewall between evidence and lifecycle/capital promotion.

    The gate is deliberately blind to metric VALUES: it reads only the
    provenance of the evidence. A spectacular backtest number therefore cannot
    buy promotion that the evidence does not support.
    """

    #: Maximum lifecycle state reachable with a given weakest provenance class.
    CEILING_BY_PROVENANCE: Dict[ProvenanceClass, AlphaLifecycleState] = {
        ProvenanceClass.MEASURED_CERTIFIED_DATA: AlphaLifecycleState.QUALIFIED,
        ProvenanceClass.MEASURED_UNCERTIFIED_DATA: AlphaLifecycleState.OOS,
        ProvenanceClass.MODEL_DERIVED: AlphaLifecycleState.RESEARCH,
        ProvenanceClass.SYNTHETIC: AlphaLifecycleState.RESEARCH,
        ProvenanceClass.HARDCODED_UNSOURCED: AlphaLifecycleState.DISCOVERED,
        ProvenanceClass.UNAVAILABLE: AlphaLifecycleState.RESEARCH,
    }

    def evaluate(
        self,
        alpha_id: str,
        ledger: EvidenceLedger,
        requested_state: AlphaLifecycleState,
    ) -> PromotionDecision:
        violations: List[str] = []

        if not ledger.records:
            return PromotionDecision(
                alpha_id=alpha_id,
                requested_state=requested_state,
                allowed_state=AlphaLifecycleState.RESEARCH,
                approved=False,
                violations=["NO_EVIDENCE_RECORDS_SUPPLIED"],
                provenance_summary={},
            )

        weakest = ledger.weakest_provenance()
        assert weakest is not None
        ceiling = self.CEILING_BY_PROVENANCE[weakest]

        if not ledger.is_empirically_measured():
            violations.append("REQUIRED_ECONOMIC_METRICS_NOT_EMPIRICALLY_MEASURED")
        if weakest not in EMPIRICAL_PROVENANCE:
            violations.append(f"NON_EMPIRICAL_EVIDENCE_PRESENT:{weakest.value}")

        order = list(AlphaLifecycleState)
        allowed = ceiling if order.index(ceiling) < order.index(requested_state) else requested_state
        approved = (allowed == requested_state) and not violations

        return PromotionDecision(
            alpha_id=alpha_id,
            requested_state=requested_state,
            allowed_state=allowed,
            approved=approved,
            violations=violations,
            provenance_summary=ledger.provenance_summary(),
        )


def provenance_of_metric(
    ledger: EvidenceLedger, metric: str, partition: Optional[str] = None
) -> Optional[ProvenanceClass]:
    """Returns the strongest provenance recorded for a metric, if any."""
    by_metric = ledger.metrics() if partition is None else ledger.metrics_at(partition)
    records = by_metric.get(metric)
    if not records:
        return None
    order = list(ProvenanceClass)
    return sorted((r.provenance for r in records), key=order.index)[0]