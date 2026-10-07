"""Family 02: Structure + Key Zone + Phase.

Requires price interaction with dealing range key zones:
- Longs: Discount zone (< 50% dealing range equilibrium)
- Shorts: Premium zone (> 50% dealing range equilibrium)
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureZonePhaseFamily(BaseStrategyFamily):
    """Family 02: Structure + Zone + Phase."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        phase_mode: str = "PULLBACK",
        min_target_r: float = 4.0,
    ):
        super().__init__(
            family_id="F02_STRUCTURE_ZONE_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Key Zone check: price must be actively testing MTF support/resistance key zone."""
        sr_zones = mtf_state.zones.support_resistance
        lo = mtf_state.low_price
        hi = mtf_state.high_price
        px = mtf_state.close_price

        if sr_zones:
            if direction == 1:
                return any(
                    z.is_bullish and (z.low_price * 0.99 <= px <= z.high_price * 1.01 or z.low_price <= lo <= z.high_price)
                    for z in sr_zones
                )
            elif direction == -1:
                return any(
                    not z.is_bullish and (z.low_price * 0.99 <= px <= z.high_price * 1.01 or z.low_price <= hi <= z.high_price)
                    for z in sr_zones
                )

        # Fallback to strict deep discount (<0.40) or premium (>0.60)
        pd_zone = mtf_state.zones.premium_discount_zone
        if direction == 1 and pd_zone == "DISCOUNT":
            return True
        elif direction == -1 and pd_zone == "PREMIUM":
            return True
        return False

