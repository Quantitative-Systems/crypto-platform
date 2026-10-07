"""
Quantitative Crypto Platform (QCP) — Platform Core Package.
Shared domain primitives, alpha representation contracts, evidence provenance,
and governance foundations used across all QCP subsystems.
"""

from platform_core.alpha_genome import (
    AlphaGenome,
    AlphaFamily,
    AlphaLifecycleState,
    MicrostructureProfile,
    EconomicPerformance,
)
from platform_core.evidence_provenance import (
    EvidenceLedger,
    EvidenceRecord,
    PromotionGate,
    PromotionDecision,
    ProvenanceClass,
    provenance_of_metric,
)

__all__ = [
    "AlphaGenome",
    "AlphaFamily",
    "AlphaLifecycleState",
    "MicrostructureProfile",
    "EconomicPerformance",
    "EvidenceLedger",
    "EvidenceRecord",
    "PromotionGate",
    "PromotionDecision",
    "ProvenanceClass",
    "provenance_of_metric",
]
