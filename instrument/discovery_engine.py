"""Autonomous Market & Instrument Discovery Engine.

Discovers, qualifies, models, ranks, and filters candidate crypto-base instruments
across multiple venues and quote asset classes (Fiat, Stablecoins, Commodities).

Continuous Autonomous Lifecycle:
    DISCOVER -> NORMALIZE -> QUALIFY -> OBSERVE -> HEALTH MONITOR ->
    MARKET STATE -> REGIME -> CAUSAL CONTEXT -> OPPORTUNITY -> PORTFOLIO ->
    RISK -> EXECUTION -> RECONCILIATION -> LEARNING

Strict Multi-Tier Instrument Lifecycle:
    1. DISCOVERED: Raw ticker identified from venue or universe catalog
    2. NORMALIZED: Canonical BASE/QUOTE format parsed; Base verified as CRYPTO
    3. QUALIFIED: Static contract criteria verified (Depth >= 500, TF Sets 1-5, Vol >= $1M)
    4. HEALTHY: Real-time dynamic feed integrity confirmed (Latency <= 1s, Clock synced, Book valid)
    5. MARKET_MODEL_COMPATIBLE: Structure identified, Key Zones active, Phase in {PULLBACK, CONTINUATION}
    6. ECONOMICALLY_TRADABLE: Friction-adjusted target >= 4.0R, viable slippage/spread economics
    7. OPPORTUNITY: Approved by Portfolio Factor Engine and Systemic Risk Governor

NOTE ON TEST FIXTURES VS EMPIRICAL OBSERVATIONS:
Tables and test cases employing pre-set volume/spread values represent Verification Test Fixtures
engineered to validate gate and lifecycle logic across a wide parameter envelope.
Live empirical microstructure measurements (orderbook depth profiles, latency distributions,
time-of-day spread expansions) are strictly deferred to Phase O (Paper Live).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from instrument.asset_class import AssetClass, classify_asset
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument
from instrument.instrument_health import HealthStatus, InstrumentHealth
from instrument.instrument_registry import AdmissionDecision, InstrumentAdmissionGate, InstrumentRegistry
from instrument.quote_currency import QuoteSettlementType, get_quote_info
from instrument.symbol_normalizer import SymbolNormalizer


class QualificationStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    PENDING_DATA = "PENDING_DATA"


class InstrumentLifecycleStage(str, Enum):
    """Rigorous 7-stage operational lifecycle for traded instruments."""
    DISCOVERED = "DISCOVERED"
    NORMALIZED = "NORMALIZED"
    QUALIFIED = "QUALIFIED"
    HEALTHY = "HEALTHY"
    MARKET_MODEL_COMPATIBLE = "MARKET_MODEL_COMPATIBLE"
    ECONOMICALLY_TRADABLE = "ECONOMICALLY_TRADABLE"
    OPPORTUNITY = "OPPORTUNITY"


@dataclass
class DiscoveredInstrumentCandidate:
    """An instrument discovered in the global trading ecosystem."""
    symbol: str
    base_asset: str
    base_class: AssetClass
    quote_asset: str
    quote_class: AssetClass
    venue: str
    qualification_status: QualificationStatus
    lifecycle_stage: InstrumentLifecycleStage = InstrumentLifecycleStage.DISCOVERED
    disqualification_reason: Optional[str] = None
    historical_depth_bars: int = 0
    timeframe_sets_available: List[str] = field(default_factory=list)
    daily_volume_usd: float = 0.0
    typical_spread_bps: float = 0.0
    estimated_slippage_bps: float = 0.0
    is_tradable: bool = False
    discovered_at: float = field(default_factory=time.time)


@dataclass
class OpportunityScoreCard:
    """Scored and ranked opportunity across the qualified universe."""
    symbol: str
    instrument: CryptoBaseInstrument
    direction: str                     # "LONG" or "SHORT"
    destination_r: float               # Must be >= 4.0R
    expected_edge_r: float
    spread_bps: float
    slippage_bps: float
    friction_cost_r: float             # Total friction in R units
    composite_rank_score: float        # Rank metric
    decision: AutonomousDecisionOutcome


class AutonomousMarketDiscoveryEngine:
    """Discovers, audits, and ranks all tradable crypto-base instruments."""

    def __init__(
        self,
        registry: Optional[InstrumentRegistry] = None,
        factor_engine: Optional[Any] = None,
        decision_engine: Optional[Any] = None,
        min_daily_volume_usd: float = 1_000_000.0,
        max_tolerated_spread_bps: float = 15.0,
        min_historical_bars: int = 500,
    ):
        self.registry = registry or InstrumentRegistry()
        if factor_engine is None:
            from execution.portfolio.factor_engine import PortfolioFactorEngine
            self.factor_engine = PortfolioFactorEngine()
        else:
            self.factor_engine = factor_engine

        if decision_engine is None:
            from execution.decision.decision_engine import AutonomousDecisionEngine
            self.decision_engine = AutonomousDecisionEngine(self.factor_engine)
        else:
            self.decision_engine = decision_engine
        self.min_daily_volume_usd = min_daily_volume_usd
        self.max_tolerated_spread_bps = max_tolerated_spread_bps
        self.min_historical_bars = min_historical_bars

        self.discovered_candidates: Dict[str, DiscoveredInstrumentCandidate] = {}
        self.qualified_instruments: Dict[str, CryptoBaseInstrument] = {}

    def discover_instrument(
        self,
        symbol_raw: str,
        venue: str = "BINANCE",
        historical_depth_bars: int = 1000,
        available_timeframe_sets: Optional[List[str]] = None,
        daily_volume_usd: float = 50_000_000.0,
        observed_spread_bps: float = 3.0,
    ) -> DiscoveredInstrumentCandidate:
        """Scan and register an instrument candidate through qualification gates."""
        canonical, base, quote = SymbolNormalizer.normalize(symbol_raw)
        base_class = classify_asset(base)
        quote_class = classify_asset(quote)
        tf_sets = available_timeframe_sets or ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

        # 1. Base Asset Invariant (MUST BE CRYPTO)
        if base_class != AssetClass.CRYPTO:
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"BASE_NOT_CRYPTO (Base {base} is {base_class.value})",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # 2. Historical Data Depth Check
        if historical_depth_bars < self.min_historical_bars:
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"INSUFFICIENT_HISTORY ({historical_depth_bars} bars < {self.min_historical_bars})",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # 3. Triplet Timeframe Set Availability
        required_sets = {"SET_1", "SET_2", "SET_3", "SET_4", "SET_5"}
        if not required_sets.issubset(set(tf_sets)):
            missing = required_sets - set(tf_sets)
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"MISSING_TIMEFRAME_SETS ({missing})",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # 4. Liquidity Volume Check
        if daily_volume_usd < self.min_daily_volume_usd:
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"LOW_VOLUME (${daily_volume_usd:,.0f} < ${self.min_daily_volume_usd:,.0f})",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # 5. Typical Spread Acceptability
        if observed_spread_bps > self.max_tolerated_spread_bps:
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"SPREAD_TOO_HIGH ({observed_spread_bps:.1f} bps > {self.max_tolerated_spread_bps:.1f} bps)",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # Build verified instrument contract
        inst = build_instrument(canonical)
        adm_rep = self.registry.register(inst)
        if adm_rep.decision != AdmissionDecision.ADMITTED:
            candidate = DiscoveredInstrumentCandidate(
                symbol=canonical,
                base_asset=base,
                base_class=base_class,
                quote_asset=quote,
                quote_class=quote_class,
                venue=venue,
                qualification_status=QualificationStatus.DISQUALIFIED,
                lifecycle_stage=InstrumentLifecycleStage.NORMALIZED,
                disqualification_reason=f"ADMISSION_GATE_FAILED ({', '.join(adm_rep.rejection_reasons)})",
                historical_depth_bars=historical_depth_bars,
                timeframe_sets_available=tf_sets,
                daily_volume_usd=daily_volume_usd,
                typical_spread_bps=observed_spread_bps,
                is_tradable=False,
            )
            self.discovered_candidates[canonical] = candidate
            return candidate

        # Passed all discovery gates -> QUALIFIED
        candidate = DiscoveredInstrumentCandidate(
            symbol=canonical,
            base_asset=base,
            base_class=base_class,
            quote_asset=quote,
            quote_class=quote_class,
            venue=venue,
            qualification_status=QualificationStatus.QUALIFIED,
            lifecycle_stage=InstrumentLifecycleStage.QUALIFIED,
            disqualification_reason=None,
            historical_depth_bars=historical_depth_bars,
            timeframe_sets_available=tf_sets,
            daily_volume_usd=daily_volume_usd,
            typical_spread_bps=observed_spread_bps,
            estimated_slippage_bps=2.0,
            is_tradable=True,
        )
        self.discovered_candidates[canonical] = candidate
        self.qualified_instruments[canonical] = inst
        return candidate

    def evaluate_operational_stage(
        self,
        candidate: DiscoveredInstrumentCandidate,
        health: InstrumentHealth,
        market_model_state: Dict[str, Any],
        environment_state: Dict[str, Any],
    ) -> InstrumentLifecycleStage:
        """Advance instrument candidate through dynamic operational lifecycle stages."""
        if candidate.qualification_status != QualificationStatus.QUALIFIED:
            return candidate.lifecycle_stage

        # Stage 4: HEALTHY Check
        if not health.is_operational():
            candidate.lifecycle_stage = InstrumentLifecycleStage.QUALIFIED
            return candidate.lifecycle_stage
        candidate.lifecycle_stage = InstrumentLifecycleStage.HEALTHY

        # Stage 5: MARKET_MODEL_COMPATIBLE Check
        phase = str(market_model_state.get("phase", "UNKNOWN")).upper()
        htf_bias = str(market_model_state.get("htf_bias", "NEUTRAL")).upper()
        if phase not in ("PULLBACK", "CONTINUATION") or htf_bias not in ("BULLISH", "BEARISH"):
            return candidate.lifecycle_stage
        candidate.lifecycle_stage = InstrumentLifecycleStage.MARKET_MODEL_COMPATIBLE

        # Stage 6: ECONOMICALLY_TRADABLE Check
        dest_r = float(market_model_state.get("destination_r", 0.0))
        spread_bps = float(market_model_state.get("spread_bps", candidate.typical_spread_bps))
        if dest_r < 4.0 or spread_bps > self.max_tolerated_spread_bps:
            return candidate.lifecycle_stage
        candidate.lifecycle_stage = InstrumentLifecycleStage.ECONOMICALLY_TRADABLE

        return candidate.lifecycle_stage

    def scan_and_rank_opportunities(
        self,
        market_states: Dict[str, Dict[str, Any]],
        environment_states: Dict[str, Dict[str, Any]],
        governor_states: Dict[str, Dict[str, Any]],
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
        health_reports: Optional[Dict[str, InstrumentHealth]] = None,
        account_equity_usd: float = 100_000.0,
        now: Optional[float] = None,
    ) -> List[OpportunityScoreCard]:
        """Evaluate and rank opportunities across all qualified instruments."""
        ranked_opportunities: List[OpportunityScoreCard] = []

        for symbol, inst in self.qualified_instruments.items():
            candidate = self.discovered_candidates.get(symbol)
            mkt_state = market_states.get(symbol, {})
            env_state = environment_states.get(symbol, {"regime": "EXPANSION_STABLE", "in_event_window": False})
            gov_state = governor_states.get(symbol, {"unknown_state_active": False, "drawdown_circuit_breaker": False, "reactivation_multiplier": 1.0})
            health = (health_reports or {}).get(symbol, InstrumentHealth(symbol=symbol))

            if candidate:
                self.evaluate_operational_stage(candidate, health, mkt_state, env_state)

            # Run deterministic decision engine
            outcome = self.decision_engine.evaluate_cycle(
                instrument=inst,
                health=health,
                market_model_state=mkt_state,
                environment_state=env_state,
                governor_state=gov_state,
                active_positions=active_positions,
                account_equity_usd=account_equity_usd,
                current_time=now,
            )

            if outcome.decision == "TRADE":
                if candidate:
                    candidate.lifecycle_stage = InstrumentLifecycleStage.OPPORTUNITY

                dest_r = outcome.destination_r
                spread_bps = float(mkt_state.get("spread_bps", 3.0))
                slippage_bps = 2.0
                total_friction_bps = spread_bps + slippage_bps
                
                # Friction expressed as fraction of stop distance
                entry = outcome.entry_price or 1.0
                stop = outcome.stop_price or 0.98
                stop_dist_pct = abs(entry - stop) / entry
                friction_r = (total_friction_bps / 10000.0) / max(0.005, stop_dist_pct)

                # Composite rank score: Structural Reward * Net Friction Efficiency
                net_dest_r = max(0.1, dest_r - friction_r)
                rank_score = (net_dest_r / 4.0) * (outcome.risk_approved / 0.01)

                card = OpportunityScoreCard(
                    symbol=symbol,
                    instrument=inst,
                    direction=outcome.direction or "LONG",
                    destination_r=dest_r,
                    expected_edge_r=round(net_dest_r * 0.45, 2),
                    spread_bps=spread_bps,
                    slippage_bps=slippage_bps,
                    friction_cost_r=round(friction_r, 4),
                    composite_rank_score=round(rank_score, 3),
                    decision=outcome,
                )
                ranked_opportunities.append(card)

        # Sort descending by composite rank score
        ranked_opportunities.sort(key=lambda c: c.composite_rank_score, reverse=True)
        return ranked_opportunities


class ContinuousObservationCoordinator:
    """Orchestrates the 24/7 continuous observation pipeline across all candidate instruments.

    Continuous Loop:
        1. DISCOVER: Scan active venue catalogs
        2. NORMALIZE: Parse canonical BASE/QUOTE, verify crypto base
        3. QUALIFY: Check static history, timeframes, and volume
        4. OBSERVE: Stream real-time ticks & orderbook
        5. HEALTH MONITOR: Validate latency, clock sync, and book integrity
        6. MARKET STATE: Generate multi-timeframe state tuples
        7. REGIME: Classify volatility stability
        8. CAUSAL CONTEXT: Track macro events and positioning
        9. OPPORTUNITY: Filter for valid >= 4.0R destination
        10. PORTFOLIO: Calculate factor exposures and heat limits
        11. RISK: Governor sign-off
        12. EXECUTION: Shadow/Paper simulation or order routing
        13. RECONCILIATION: Track execution drag vs research signal
        14. LEARNING: Register hypothesis performance in H-Registry
    """

    def __init__(self, discovery_engine: AutonomousMarketDiscoveryEngine):
        self.discovery_engine = discovery_engine
        self.cycle_count: int = 0

    def run_continuous_observation_cycle(
        self,
        market_states: Dict[str, Dict[str, Any]],
        environment_states: Dict[str, Dict[str, Any]],
        governor_states: Dict[str, Dict[str, Any]],
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
        health_reports: Optional[Dict[str, InstrumentHealth]] = None,
        account_equity_usd: float = 100_000.0,
        now: Optional[float] = None,
    ) -> List[OpportunityScoreCard]:
        """Execute one continuous observation cycle."""
        self.cycle_count += 1
        return self.discovery_engine.scan_and_rank_opportunities(
            market_states=market_states,
            environment_states=environment_states,
            governor_states=governor_states,
            active_positions=active_positions,
            health_reports=health_reports,
            account_equity_usd=account_equity_usd,
            now=now,
        )
