"""
Product 01: Crypto Platform - Strategy B: Continuation Riding Engine
Implements Strategy B rules with MTF Premium/Discount Valuation Filtering.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, KeyZone


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
        1. MTF trend must be aligned with HTF Bias.
        2. Premium/Discount Valuation:
           - SELL requires price in MTF Premium Zone (top 50% of MTF swing range).
           - BUY requires price in MTF Discount Zone (bottom 50% of MTF swing range).
        3. Active unmitigated MTF KeyZone present inside Premium/Discount zone.
        """
        if htf_state.trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF trend is not trending.")

        # Rule 1: MTF Trend must be aligned with HTF Bias
        if mtf_state.trend != htf_state.trend:
            return StrategyBResult(
                is_valid_setup=False, mtf_keyzone=None,
                reason=f"MTF trend ({mtf_state.trend.value}) opposes HTF bias ({htf_state.trend.value})."
            )

        # Rule 2: Premium / Discount Valuation Check
        if mtf_state.protected_high and mtf_state.protected_low:
            swing_range = mtf_state.protected_high - mtf_state.protected_low
            if swing_range > 0:
                current_price = mtf_state.current_price
                equilibrium = mtf_state.protected_low + (swing_range * 0.5)

                # SELL requires price to be in Premium (Above 50% Equilibrium)
                if htf_state.trend == TrendDirection.BEARISH and current_price < equilibrium:
                    return StrategyBResult(
                        is_valid_setup=False, mtf_keyzone=None,
                        reason=f"Valuation Error: Cannot SELL in MTF Discount Zone (${current_price:.2f} < Equilibrium ${equilibrium:.2f})."
                    )

                # BUY requires price to be in Discount (Below 50% Equilibrium)
                if htf_state.trend == TrendDirection.BULLISH and current_price > equilibrium:
                    return StrategyBResult(
                        is_valid_setup=False, mtf_keyzone=None,
                        reason=f"Valuation Error: Cannot BUY in MTF Premium Zone (${current_price:.2f} > Equilibrium ${equilibrium:.2f})."
                    )

        # Rule 3: Active unmitigated MTF Keyzone in trend direction
        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_state.trend and not z.is_mitigated
        ]

        if not matching_zones:
            return StrategyBResult(
                is_valid_setup=False, mtf_keyzone=None,
                reason="No unmitigated MTF Keyzone found for Continuation entry."
            )

        return StrategyBResult(
            is_valid_setup=True,
            mtf_keyzone=matching_zones[-1],
            reason="Strategy B (Continuation Riding) Setup Verified in Premium/Discount Zone."
        )