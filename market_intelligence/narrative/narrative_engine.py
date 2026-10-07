"""Market Narrative Engine: Machine-Readable Causal Narrative Synthesis.

Synthesizes technical structure, macro drivers, positioning, and event clock context
into an institutional-grade, human-interpretable narrative state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from market_intelligence.cross_market.cross_market_engine import CrossMarketSnapshot
from market_intelligence.events.contracts import EventTimeContext
from market_intelligence.positioning.positioning_engine import PositioningSnapshot
from market_intelligence.regimes.regime_contracts import MarketRegimeSnapshot
from market_model.contracts import MarketState


@dataclass
class MarketNarrativeState:
    """Standardized machine-readable narrative representation."""
    timestamp_ms: int
    symbol: str
    primary_driver: str
    secondary_driver: str
    risk_regime: str
    crypto_regime: str
    current_technical_state: str
    mtf_state: str
    ltf_trigger: str
    upcoming_risk: str
    confidence: str                       # "LOW", "MEDIUM", "HIGH"
    invalidation: str
    narrative_summary: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "symbol": self.symbol,
            "primary_driver": self.primary_driver,
            "secondary_driver": self.secondary_driver,
            "risk_regime": self.risk_regime,
            "crypto_regime": self.crypto_regime,
            "current_technical_state": self.current_technical_state,
            "mtf_state": self.mtf_state,
            "ltf_trigger": self.ltf_trigger,
            "upcoming_risk": self.upcoming_risk,
            "confidence": self.confidence,
            "invalidation": self.invalidation,
            "narrative_summary": self.narrative_summary,
            "meta": self.meta,
        }


class MarketNarrativeEngine:
    """Deterministic and LLM-assisted causal narrative synthesizer."""

    def synthesize_narrative(
        self,
        symbol: str,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: Optional[MarketState],
        regime: MarketRegimeSnapshot,
        cross_market: Optional[CrossMarketSnapshot],
        positioning: Optional[PositioningSnapshot],
        event_context: Optional[EventTimeContext],
        external_ai_summary: Optional[str] = None,
    ) -> MarketNarrativeState:
        """Construct the full institutional narrative state."""
        ts_ms = htf_state.timestamp_ms

        # 1. Primary Driver
        if cross_market and abs(cross_market.btc_dxy_correlation_30d) > 0.50 and abs(cross_market.dxy_change_pct_24h) > 0.3:
            primary_driver = f"US Monetary Policy & Dollar Repricing (DXY {cross_market.dxy_change_pct_24h:+.2f}%)"
        elif cross_market and cross_market.etf_net_inflow_usd_24h != 0.0:
            inflow_millions = cross_market.etf_net_inflow_usd_24h / 1e6
            primary_driver = f"Institutional ETF Liquidity Flows (${inflow_millions:+.1f}M / 24h)"
        elif positioning and positioning.trapped_setup.value != "NONE":
            primary_driver = f"Derivatives Positioning Dislocation ({positioning.trapped_setup.value})"
        else:
            primary_driver = f"Internal Technical Market Structure ({htf_state.structure.external_trend.value})"

        # 2. Secondary Driver
        if positioning and positioning.funding_state.value != "NEUTRAL":
            secondary_driver = f"Perpetual Funding Rate Imbalance ({positioning.funding_rate_8h_bps:+.1f} bps / 8h)"
        elif cross_market and cross_market.active_divergence:
            secondary_driver = f"Cross-Asset Divergence ({cross_market.active_divergence})"
        else:
            secondary_driver = f"Liquidity Distribution ({mtf_state.zones.premium_discount_zone})"

        # 3. Technical State Descriptions
        htf_tech = f"HTF {htf_state.structure.external_trend.value} ({htf_state.phase.current_phase.value})"
        mtf_tech = f"MTF {mtf_state.phase.current_phase.value} in {mtf_state.zones.premium_discount_zone}"
        
        if ltf_state:
            recent_break = ltf_state.structure.recent_breaks[0].break_type.value if ltf_state.structure.recent_breaks else "NONE"
            ltf_tech = f"LTF {ltf_state.structure.internal_trend.value} (Break: {recent_break})"
        else:
            ltf_tech = "Pending LTF Confirmation"

        # 4. Upcoming Risk from Event Clock
        if event_context and event_context.nearest_upcoming_event and event_context.time_to_upcoming_ms is not None:
            hours_away = event_context.time_to_upcoming_ms / (1000 * 3600)
            upcoming_risk = (
                f"{event_context.nearest_upcoming_event.event_name} in {hours_away:.1f}h "
                f"[{event_context.clock_phase.value}]"
            )
        else:
            upcoming_risk = "No high-impact scheduled catalyst within 24 hours"

        # 5. Invalidation Criteria
        invalid_level = (
            htf_state.structure.protected_low
            if htf_state.structure.external_trend.value == "BULLISH"
            else htf_state.structure.protected_high
        )
        invalidation = (
            f"HTF structural break beyond {invalid_level} OR macro liquidity shock"
            if invalid_level
            else "HTF structural change of character"
        )

        # 6. Overall Confidence
        if event_context and event_context.is_trading_prohibited:
            confidence = "LOW"
        elif regime.is_favorable_for_trend_following and (not positioning or positioning.edge_alignment_score >= 1.0):
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"

        # 7. Human-readable narrative summary
        summary = (
            f"Asset {symbol} operating in {regime.risk.value} risk regime and {regime.correlation.value} correlation mode. "
            f"Primary macro driver: {primary_driver}. Secondary: {secondary_driver}. "
            f"Technical Spine: {htf_tech} -> {mtf_tech} -> {ltf_tech}. "
            f"Risk Catalyst: {upcoming_risk}. System confidence: {confidence}."
        )
        if external_ai_summary:
            summary += f" [AI Annotation: {external_ai_summary}]"

        return MarketNarrativeState(
            timestamp_ms=ts_ms,
            symbol=symbol,
            primary_driver=primary_driver,
            secondary_driver=secondary_driver,
            risk_regime=regime.risk.value,
            crypto_regime=regime.correlation.value,
            current_technical_state=htf_tech,
            mtf_state=mtf_tech,
            ltf_trigger=ltf_tech,
            upcoming_risk=upcoming_risk,
            confidence=confidence,
            invalidation=invalidation,
            narrative_summary=summary,
        )
