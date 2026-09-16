"""
QCP Autonomous Research Factory.
Generates alpha *specifications* — never alpha results.

Governance contract (enforced by platform_core.evidence_provenance):
    This module is FORBIDDEN from asserting performance. Every genome it emits
    carries EconomicPerformance() with all-zero values and the lifecycle state
    RESEARCH. Metrics may only be attached afterwards by
    research.economic_evaluation_engine, which computes them from certified
    market data and stamps them with an EvidenceRecord.

The factory's job is to ask economically-grounded questions, not to answer
them. A specification that cannot be measured with data the platform actually
holds is still emitted — but flagged with its missing data dependency so it is
never mistaken for a testable candidate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    AlphaLifecycleState,
    EconomicPerformance,
    MicrostructureProfile,
)


@dataclass
class AlphaSpecification:
    """Declarative hypothesis: what to test, on what data, and why it should exist."""

    alpha_id: str
    family: AlphaFamily
    version: str
    asset_universe: List[str]
    venues: List[str]
    instruments: List[str]
    timeframe: str
    expected_holding_period_hours: float
    economic_rationale: str
    features: List[str]
    entry_mechanism: str
    exit_mechanism: str
    required_data: List[str]
    regime_hypotheses: Dict[str, float] = field(default_factory=dict)
    failure_modes: List[str] = field(default_factory=list)


#: The declared alpha research population. No performance numbers appear here,
#: by construction: there is nothing to fabricate.
ALPHA_SPECIFICATIONS: List[AlphaSpecification] = [
    AlphaSpecification(
        alpha_id="FAM-07-MTFCONT_SOLUSDT_Set2",
        family=AlphaFamily.DIRECTIONAL,
        version="v2.1",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT", "PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=36.0,
        economic_rationale=(
            "Persistent crypto trends are driven by order-flow herding and slow "
            "allocator rebalancing. A shallow retracement inside an established "
            "trend offers continuation exposure without buying the extension."
        ),
        features=["ema_fast_slope", "ema_slow_slope", "atr_pullback_distance"],
        entry_mechanism=(
            "Bar-close confirmed: fast EMA above rising slow EMA and close retraced "
            "into the fast EMA band. Executed at next-bar open (causal)."
        ),
        exit_mechanism="ATR-based stop (2.0x ATR) with 2.0R target or time stop.",
        required_data=["OHLCV_4h_SOL"],
        regime_hypotheses={"BULL_MOMENTUM": 0.85, "SIDEWAYS_CHOP": -0.30},
        failure_modes=["TREND_FAILURE", "WHIPSAW_IN_CHOP", "LATENCY_SENSITIVE"],
    ),
    AlphaSpecification(
        alpha_id="FAM-06-VOLSQUEEZE_SOLUSDT_V1",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.1",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale=(
            "Volatility clusters and mean-reverts. Compression raises the conditional "
            "probability of an expansion move; trading the range break captures the "
            "expansion while an ATR stop bounds risk."
        ),
        features=["atr_percentile", "range_breakout_distance"],
        entry_mechanism=(
            "Bar-close confirmed: ATR percentile below squeeze threshold and close "
            "breaks the prior N-bar extreme. Executed at next-bar open (causal)."
        ),
        exit_mechanism="ATR-based stop (2.0x ATR) with 2.0R target or time stop.",
        required_data=["OHLCV_4h_SOL"],
        regime_hypotheses={"LOW_VOL_COMPRESSION": 0.90, "VOL_EXPLOSION": -0.20},
        failure_modes=["FALSE_BREAKOUT", "REGIME_FLIP", "COMMON_VOL_FACTOR"],
    ),
    AlphaSpecification(
        alpha_id="FAM-09-RV_COINT_ETH_BTC_V2",
        family=AlphaFamily.RELATIVE_VALUE,
        version="v2.0",
        asset_universe=["ETH/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT"],
        timeframe="4h",
        expected_holding_period_hours=48.0,
        economic_rationale=(
            "ETH and BTC share a dominant common crypto factor; transient divergences "
            "in their log-price ratio are driven by idiosyncratic flow and are "
            "compensated to revert."
        ),
        features=["log_ratio_zscore"],
        entry_mechanism=(
            "Bar-close confirmed: ratio z-score beyond entry threshold; executed at "
            "next-bar open on the ETH leg (causal)."
        ),
        exit_mechanism="ATR-based stop with 2.0R target or time stop.",
        required_data=["OHLCV_4h_ETH", "OHLCV_4h_BTC"],
        regime_hypotheses={"DISPERSED_MARKET": 0.80, "CORRELATED_CRASH": -0.40},
        failure_modes=["REGIME_BREAK_NO_REVERSION", "STRUCTURAL_REPRICING"],
    ),
    AlphaSpecification(
        alpha_id="FAM-10-DYNAMIC_CARRY_SOL_V2",
        family=AlphaFamily.CARRY,
        version="v2.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT", "PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=72.0,
        economic_rationale=(
            "Perpetual funding transfers a premium from crowded directional "
            "positioning to liquidity providers. When net funding exceeds borrow plus "
            "roundtrip friction, a delta-neutral spot/perp carry is compensated."
        ),
        features=["funding_rate_apr", "spot_perp_basis", "borrow_interest_rate"],
        entry_mechanism="Harvest when net funding APR clears borrow + friction hurdle.",
        exit_mechanism="Exit when net funding APR decays below the hurdle.",
        required_data=["FUNDING_RATE_HISTORY", "SPOT_PERP_BASIS"],
        regime_hypotheses={"EXTREME_POSITIVE_FUNDING": 0.95},
        failure_modes=["FUNDING_REGIME_FLIP", "BASIS_DISLOCATION", "BORROW_ILLIQUIDITY"],
    ),
    AlphaSpecification(
        alpha_id="FAM-12-OFI_MOMENTUM_BTC_V1",
        family=AlphaFamily.MICROSTRUCTURE,
        version="v1.0",
        asset_universe=["BTC/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="15m",
        expected_holding_period_hours=2.0,
        economic_rationale=(
            "Aggressive taker flow into thinning book depth produces short-horizon "
            "price pressure that is compensated to persist briefly before liquidity "
            "replenishes."
        ),
        features=["order_flow_imbalance", "l2_depth_imbalance"],
        entry_mechanism="Enter when standardized order-flow imbalance exceeds threshold.",
        exit_mechanism="Fixed time stop or book-pressure reversal.",
        required_data=["L2_ORDER_BOOK_DEPTH_TICK", "AGGRESSOR_FLOW"],
        regime_hypotheses={"NORMAL_VOL": 0.70},
        failure_modes=["LATENCY_FATAL", "QUEUE_POSITION_UNMODELED", "ADVERSE_SELECTION"],
    ),
]


class AutonomousResearchFactory:
    """
    Emits machine-readable alpha specifications with zero asserted performance.

    Availability of the required data is resolved by the caller (the
    orchestrator) against the certified warehouse, so a specification is never
    silently upgraded into a measured candidate.
    """

    def __init__(self, certified_universe: Optional[List[str]] = None):
        self.certified_universe = certified_universe or ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    def get_specifications(self) -> List[AlphaSpecification]:
        return list(ALPHA_SPECIFICATIONS)

    def get_data_requirements(self) -> Dict[str, List[str]]:
        return {s.alpha_id: list(s.required_data) for s in ALPHA_SPECIFICATIONS}

    @staticmethod
    def _to_genome(spec: AlphaSpecification) -> AlphaGenome:
        return AlphaGenome(
            alpha_id=spec.alpha_id,
            family=spec.family,
            version=spec.version,
            asset_universe=list(spec.asset_universe),
            venues=list(spec.venues),
            instruments=list(spec.instruments),
            timeframe=spec.timeframe,
            expected_holding_period_hours=spec.expected_holding_period_hours,
            economic_rationale=spec.economic_rationale,
            features=list(spec.features),
            entry_mechanism=spec.entry_mechanism,
            exit_mechanism=spec.exit_mechanism,
            microstructure=MicrostructureProfile(),
            # ZERO performance: metrics are attached only by the evaluation engine.
            performance=EconomicPerformance(),
            regime_dependencies=dict(spec.regime_hypotheses),
            failure_modes=list(spec.failure_modes),
            lifecycle_state=AlphaLifecycleState.RESEARCH,
        )

    def generate_candidate_population(
        self, current_active_families: Optional[List[str]] = None
    ) -> List[AlphaGenome]:
        """
        Generates the declared specification population, prioritising families
        that are currently under-represented in the live portfolio.
        """
        genomes = [self._to_genome(s) for s in ALPHA_SPECIFICATIONS]
        for g in genomes:
            g.compute_evidence_hash()

        if current_active_families:
            active = {f.upper() for f in current_active_families}
            genomes.sort(key=lambda g: (g.family.value in active, g.alpha_id))
        return genomes

    @staticmethod
    def _supported_data_tokens() -> set:
        """Data tokens the platform can currently serve from its own warehouse."""
        tokens = set()
        for tf in ("1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"):
            for sym in ("BTC", "ETH", "SOL"):
                tokens.add(f"OHLCV_{tf}_{sym}")
        return tokens

    def get_research_gap_analysis(self, current_population: List[AlphaGenome]) -> Dict[str, Any]:
        """Identifies underrepresented alpha families and unsupported data needs."""
        families_present = {g.family.value for g in current_population}
        all_families = {f.value for f in AlphaFamily}
        missing = sorted(all_families - families_present)

        unsupported_data: List[str] = []
        for spec in ALPHA_SPECIFICATIONS:
            unmet = [d for d in spec.required_data if d not in self._supported_data_tokens()]
            if unmet:
                unsupported_data.append(f"{spec.alpha_id}:{','.join(unmet)}")

        return {
            "total_candidates": len(current_population),
            "families_present": sorted(families_present),
            "missing_families": missing,
            "recommended_next_research_target": missing[0] if missing else "REFINEMENT",
            "specifications_with_unsupported_data": unsupported_data,
            # Proof that this module asserts no performance of its own.
            "asserted_performance_metrics": 0,
        }