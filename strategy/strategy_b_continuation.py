"""
Product 01: Crypto Platform - Strategy B: Continuation Riding Engine
Implements Strategy B rules with MTF Premium/Discount Valuation Filtering.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, KeyZone, MarketPhase


@dataclass
class StrategyBResult:
    is_valid_setup: bool
    mtf_keyzone: Optional[KeyZone]
    reason: str


class StrategyBContinuationEngine:

    @staticmethod
    def evaluate_continuation_setup(
        htf_state: MarketStatePayload,
        mtf_state: MarketStatePayload
    ) -> StrategyBResult:
        """
        Strategy B Rules:
        1. MTF trend is aligned with HTF bias.
        2. Price is in a favourable MTF valuation zone.
        3. Active unmitigated MTF keyzone exists.
        """
        htf_trend = htf_state.structure_state.external_trend or htf_state.trend_state.direction or htf_state.trend
        mtf_trend = mtf_state.structure_state.external_trend or mtf_state.trend_state.direction or mtf_state.trend

        if htf_trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF trend is not trending.")

        if mtf_trend != htf_trend:
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason=f"MTF trend ({mtf_trend.value}) opposes HTF bias ({htf_trend.value}).")

        if htf_state.phase_state.current_phase not in (MarketPhase.CONTINUATION, MarketPhase.EXPANSION):
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF is not in continuation or expansion.")

        if mtf_state.protected_high and mtf_state.protected_low:
            swing_range = mtf_state.protected_high - mtf_state.protected_low
            if swing_range > 0:
                current_price = mtf_state.current_price
                equilibrium = mtf_state.protected_low + (swing_range * 0.5)
                if htf_trend == TrendDirection.BEARISH and current_price < equilibrium:
                    return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason=f"Valuation error: price is still in discount for a bearish continuation.")
                if htf_trend == TrendDirection.BULLISH and current_price > equilibrium:
                    return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason=f"Valuation error: price is still in premium for a bullish continuation.")

        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_trend and not z.is_mitigated
        ]

        if not matching_zones:
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="No unmitigated MTF keyzone found for continuation entry.")

        return StrategyBResult(is_valid_setup=True, mtf_keyzone=matching_zones[-1], reason="Strategy B (Continuation Riding) setup verified.")