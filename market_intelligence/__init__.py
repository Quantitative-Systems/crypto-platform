"""Market Intelligence & Causal Context Architecture.

Implements the institutional causal context layer around the frozen Market Model:
1. Causal Event Engine & Event Clock (Expectation vs Actual, Temporal Proximity).
2. Market Regime Engine (Volatility, Liquidity, Correlation, Trend, Risk - Phase != Regime).
3. Cross-Market State Engine (DXY, Yields, SPX, NDX, Gold, Oil, VIX, ETF flows, Stablecoins).
4. Positioning Intelligence Engine (OI, Funding, Liquidations, Basis, Trapped Traders).
5. Market Narrative Engine (Machine-readable causal narrative synthesis).
6. Hypothesis Registry & Concept Drift Detector (Empirical validation, edge decay monitoring).
"""
from market_intelligence.cross_market import (
    CrossMarketSnapshot,
    CrossMarketStateEngine,
)
from market_intelligence.events import (
    CausalEvent,
    CausalEventEngine,
    EventCategory,
    EventClock,
    EventClockPhase,
    EventImportance,
    EventSurprise,
    EventTimeContext,
    SurpriseDirection,
    TransmissionChain,
)
from market_intelligence.hypotheses import (
    CausalHypothesis,
    ConceptDriftDetector,
    DriftReport,
    DriftSeverity,
    HypothesisRegistry,
    HypothesisStatus,
    ValidationVerdict,
)
from market_intelligence.narrative import (
    MarketNarrativeEngine,
    MarketNarrativeState,
)
from market_intelligence.positioning import (
    FundingState,
    PositioningIntelligenceEngine,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes import (
    CorrelationRegime,
    LiquidityRegime,
    MarketRegimeEngine,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)

__all__ = [
    # Events
    "CausalEvent",
    "CausalEventEngine",
    "EventCategory",
    "EventClock",
    "EventClockPhase",
    "EventImportance",
    "EventSurprise",
    "EventTimeContext",
    "SurpriseDirection",
    "TransmissionChain",
    # Regimes
    "CorrelationRegime",
    "LiquidityRegime",
    "MarketRegimeEngine",
    "MarketRegimeSnapshot",
    "RiskRegime",
    "TrendRegime",
    "VolatilityRegime",
    # Cross Market
    "CrossMarketSnapshot",
    "CrossMarketStateEngine",
    # Positioning
    "FundingState",
    "PositioningIntelligenceEngine",
    "PositioningSnapshot",
    "TrappedState",
    # Narrative
    "MarketNarrativeEngine",
    "MarketNarrativeState",
    # Hypotheses & Drift
    "CausalHypothesis",
    "ConceptDriftDetector",
    "DriftReport",
    "DriftSeverity",
    "HypothesisRegistry",
    "HypothesisStatus",
    "ValidationVerdict",
]
