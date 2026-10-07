"""Adaptive Causal Market Intelligence Engine.

Integrates the frozen technical core (AdaptiveEngineV1: Structure / Key Zones / Phase)
with the Causal Intelligence Layer:
- Event Clock & Catalyst Proximity Gating
- Multi-Dimensional Regime Filtering (Phase != Regime)
- Positioning & Trapped Trader Intelligence
- Decision Ledger Audit Logging
- Strict Deterministic Execution Spine (>= 4.0R floor, <= 1.0% risk)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from execution.decision_ledger import DecisionLedger, DecisionRecord, DecisionType
from market_intelligence.cross_market.cross_market_engine import (
    CrossMarketSnapshot,
    CrossMarketStateEngine,
)
from market_intelligence.events.contracts import EventTimeContext
from market_intelligence.events.event_engine import CausalEventEngine
from market_intelligence.narrative.narrative_engine import (
    MarketNarrativeEngine,
    MarketNarrativeState,
)
from market_intelligence.positioning.positioning_engine import (
    PositioningIntelligenceEngine,
    PositioningSnapshot,
)
from market_intelligence.regimes.regime_contracts import MarketRegimeSnapshot
from market_intelligence.regimes.regime_engine import MarketRegimeEngine
from market_model.contracts import MarketState
from strategy.adaptive.adaptive_engine_v1 import (
    AdaptiveDecisionAudit,
    AdaptiveEngineV1,
    AdaptiveMarketState,
)
from strategy.base import CandidateSignal


class AdaptiveCausalEngine:
    """Institutional Causal Context & Decision Engine."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        event_engine: Optional[CausalEventEngine] = None,
        regime_engine: Optional[MarketRegimeEngine] = None,
        cross_market_engine: Optional[CrossMarketStateEngine] = None,
        positioning_engine: Optional[PositioningIntelligenceEngine] = None,
        narrative_engine: Optional[MarketNarrativeEngine] = None,
        decision_ledger: Optional[DecisionLedger] = None,
        min_target_r: float = 4.0,
        risk_pct_per_trade: float = 0.01,
    ):
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label
        self.min_target_r = min_target_r
        self.risk_pct_per_trade = risk_pct_per_trade

        # Frozen Technical Adaptive Engine Core
        self.technical_core = AdaptiveEngineV1(
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            min_target_r=min_target_r,
            risk_pct_per_trade=risk_pct_per_trade,
        )

        # Intelligence Engines
        self.event_engine = event_engine or CausalEventEngine()
        self.regime_engine = regime_engine or MarketRegimeEngine()
        self.cross_market_engine = cross_market_engine or CrossMarketStateEngine()
        self.positioning_engine = positioning_engine or PositioningIntelligenceEngine()
        self.narrative_engine = narrative_engine or MarketNarrativeEngine()
        self.ledger = decision_ledger or DecisionLedger()

    def evaluate_causal_decision(
        self,
        bar_idx: int,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: MarketState,
        symbol: str,
        macro_quotes: Optional[Dict[str, Any]] = None,
        positioning_raw: Optional[Dict[str, Any]] = None,
        ai_narrative_annotation: Optional[str] = None,
    ) -> Tuple[Optional[CandidateSignal], DecisionRecord, MarketNarrativeState]:
        """Execute complete causal decision pipeline with full audit recording."""
        ts_ms = ltf_state.timestamp_ms
        blockers: List[str] = []

        # 1. Event Clock Evaluation
        event_ctx = self.event_engine.evaluate_clock_context(ts_ms, symbol=symbol)
        if event_ctx.is_trading_prohibited:
            blockers.append(f"Event Clock Gating: {event_ctx.reason}")

        # 2. Market Regime Evaluation (Phase != Regime)
        regime_snapshot = self.regime_engine.evaluate_regime(
            current_state=mtf_state,
            cross_market_data=macro_quotes,
            positioning_data=positioning_raw,
        )
        if not regime_snapshot.is_favorable_for_trend_following:
            blockers.append(
                f"Unfavorable Regime: Volatility={regime_snapshot.volatility.value}, "
                f"Liquidity={regime_snapshot.liquidity.value}, Trend={regime_snapshot.trend.value}"
            )

        # 3. Cross-Market & Macro Context
        cross_snapshot = self.cross_market_engine.evaluate_cross_market(
            timestamp_ms=ts_ms,
            macro_quotes=macro_quotes,
        )

        # 4. Technical Core Evaluation (Frozen Market Model)
        technical_signal, adaptive_audit = self.technical_core.evaluate_adaptive_decision(
            bar_index=bar_idx,
            timestamp_ms=ts_ms,
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
        )

        direction = technical_signal.direction if technical_signal else 1

        # 5. Positioning & Trapped Trader Evaluation
        pos_snapshot = self.positioning_engine.evaluate_positioning(
            timestamp_ms=ts_ms,
            positioning_raw=positioning_raw,
            technical_direction=direction,
        )

        if technical_signal and pos_snapshot.trapped_setup.value == "LONG_LIQUIDATION_RISK" and technical_signal.direction == 1:
            blockers.append("Positioning Risk: Over-leveraged longs face imminent liquidation flush")
        elif technical_signal and pos_snapshot.trapped_setup.value == "SHORT_SQUEEZE_PRIME" and technical_signal.direction == -1:
            blockers.append("Positioning Risk: Crowded shorts face imminent squeeze")

        # 6. Technical State Verification
        if not technical_signal:
            reason = adaptive_audit.reason if adaptive_audit else "No valid technical setup"
            blockers.append(f"Technical: {reason}")

        # 7. Synthesize Machine-Readable Narrative State
        narrative = self.narrative_engine.synthesize_narrative(
            symbol=symbol,
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
            regime=regime_snapshot,
            cross_market=cross_snapshot,
            positioning=pos_snapshot,
            event_context=event_ctx,
            external_ai_summary=ai_narrative_annotation,
        )

        # 8. Decision Determination & Ledger Recording
        if blockers:
            decision_record = self.ledger.record_decision(
                timestamp_ms=ts_ms,
                symbol=symbol,
                timeframe_set=self.timeframe_set_id,
                decision=DecisionType.NO_TRADE,
                primary_reason=blockers[0],
                direction=None,
                htf_context=f"{htf_state.structure.external_trend.value} ({htf_state.phase.current_phase.value})",
                mtf_context=f"{mtf_state.phase.current_phase.value} ({mtf_state.zones.premium_discount_zone})",
                ltf_context=ltf_state.structure.internal_trend.value,
                macro_context=cross_snapshot.macro_transmission_bias,
                liquidity_context=regime_snapshot.liquidity.value,
                positioning_context=pos_snapshot.funding_state.value,
                event_risk_context=event_ctx.reason,
                htf_destination_r=technical_signal.target_r if technical_signal else 0.0,
                expected_edge_r=0.0,
                risk_allocated_pct=0.0,
                blockers=blockers,
            )
            return None, decision_record, narrative

        # Candidate Trade Approved! Apply positioning sizing adjustments
        assert technical_signal is not None
        adjusted_risk = min(
            self.risk_pct_per_trade * pos_snapshot.edge_alignment_score,
            self.risk_pct_per_trade, # Strict 1.0% hard ceiling
        )

        expected_edge = 1.35 * pos_snapshot.edge_alignment_score

        decision_record = self.ledger.record_decision(
            timestamp_ms=ts_ms,
            symbol=symbol,
            timeframe_set=self.timeframe_set_id,
            decision=DecisionType.TRADE,
            primary_reason="Full Causal & Technical Alignment",
            direction="LONG" if technical_signal.direction == 1 else "SHORT",
            htf_context=f"{htf_state.structure.external_trend.value} ({htf_state.phase.current_phase.value})",
            mtf_context=f"{mtf_state.phase.current_phase.value} in {mtf_state.zones.premium_discount_zone}",
            ltf_context=f"Entry confirmation at {technical_signal.entry_price}",
            macro_context=cross_snapshot.macro_transmission_bias,
            liquidity_context=regime_snapshot.liquidity.value,
            positioning_context=pos_snapshot.trapped_setup.value if pos_snapshot.trapped_setup.value != "NONE" else pos_snapshot.funding_state.value,
            event_risk_context=event_ctx.reason,
            htf_destination_r=technical_signal.target_r,
            expected_edge_r=expected_edge,
            risk_allocated_pct=adjusted_risk,
            entry_price=technical_signal.entry_price,
            stop_price=technical_signal.stop_price,
            target_price=technical_signal.target_price,
        )

        return technical_signal, decision_record, narrative
