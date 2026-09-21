"""
Product 01: Crypto Platform - Strategy A: Pullback Riding Engine
Implements Strategy A rules with strict MTF CHOCH/BOS realignment validation.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, KeyZone, EventType, MarketPhase


@dataclass
class StrategyAResult:
    is_valid_setup: bool
    mtf_keyzone: Optional[KeyZone]
    reason: str


class StrategyAPullbackEngine:

    @staticmethod
    def evaluate_pullback_setup(
        htf_state: MarketStatePayload,
        mtf_state: MarketStatePayload
    ) -> StrategyAResult:
        """
        Strategy A Rules:
        1. HTF phase is pullback or the HTF bias is currently retracing.
        2. MTF trend has realigned back into HTF bias direction.
        3. Active unmitigated MTF keyzone exists.
        """
        htf_trend = htf_state.structure_state.external_trend or htf_state.trend_state.direction or htf_state.trend
        mtf_trend = mtf_state.structure_state.external_trend or mtf_state.trend_state.direction or mtf_state.trend

        if htf_trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF trend is not trending.")

        if htf_state.phase_state.current_phase not in (MarketPhase.PULLBACK, MarketPhase.AWAITING_CONFIRMATION):
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF is not in pullback or awaiting confirmation.")

        if mtf_trend != htf_trend:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason=f"MTF trend ({mtf_trend.value}) has not realigned with HTF bias ({htf_trend.value}).")

        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_trend and not z.is_mitigated
        ]

        if not matching_zones:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="No unmitigated MTF keyzone found for pullback entry.")

        return StrategyAResult(is_valid_setup=True, mtf_keyzone=matching_zones[-1], reason="Strategy A (Pullback Riding) setup verified.")