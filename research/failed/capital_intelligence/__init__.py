"""
Quantitative Crypto Platform (QCP) — Capital Intelligence Package.
Net-edge decomposition, confidence estimation, capacity analysis, capital feasibility,
selection scoring and factor attribution for alpha candidates.
"""

from capital_intelligence.feasibility_engine import (
    CapitalFeasibilityEngine,
    FeasibilityVerdict,
    FeasibilityEvaluation,
    BINANCE_CONSTRAINTS,
)
from capital_intelligence.alpha_capital_intelligence import (
    NetEdgeEngine,
    NetEdgeBreakdown,
    AlphaConfidenceEngine,
    AlphaConfidenceMetrics,
    ConfidenceBand,
    AlphaCapacityEngine,
    CapacityCurvePoint,
    AlphaSelectionEngine,
    FactorAttributionEngine,
    FactorAttribution,
    AlphaHealthEngine,
    AlphaHealthStatus,
)

__all__ = [
    "CapitalFeasibilityEngine",
    "FeasibilityVerdict",
    "FeasibilityEvaluation",
    "BINANCE_CONSTRAINTS",
    "NetEdgeEngine",
    "NetEdgeBreakdown",
    "AlphaConfidenceEngine",
    "AlphaConfidenceMetrics",
    "ConfidenceBand",
    "AlphaCapacityEngine",
    "CapacityCurvePoint",
    "AlphaSelectionEngine",
    "FactorAttributionEngine",
    "FactorAttribution",
    "AlphaHealthEngine",
    "AlphaHealthStatus",
]

