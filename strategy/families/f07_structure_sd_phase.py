"""Family 07: Structure + Supply/Demand + Phase (Repaired).

Requires genuine causal interaction with an active Supply or Demand origin base:
- Longs: Price actively testing or breaking/retesting an unmitigated Demand base (within 3% buffer).
- Shorts: Price actively testing or breaking/retesting an unmitigated Supply base (within 3% buffer).
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureSupplyDemandPhaseFamily(BaseStrategyFamily):
    """Family 07: Structure + Supply/Demand + Phase."""

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
            family_id="F07_STRUCTURE_SUPPLY_DEMAND_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal Supply/Demand base interaction check."""
        sd_zones = mtf_state.zones.supply_demand or mtf_state.zones.support_resistance
        if not sd_zones:
            return False

        px = mtf_state.close_price
        lo = mtf_state.low_price
        hi = mtf_state.high_price

        if direction == 1:
            return any(
                z.is_bullish
                and not z.is_mitigated
                and (z.low_price * 0.97 <= px <= z.high_price * 1.05 or (lo <= z.high_price * 1.03 and px >= z.low_price * 0.97))
                for z in sd_zones
            )
        elif direction == -1:
            return any(
                not z.is_bullish
                and not z.is_mitigated
                and (z.low_price * 0.95 <= px <= z.high_price * 1.03 or (hi >= z.low_price * 0.97 and px <= z.high_price * 1.03))
                for z in sd_zones
            )
        return False
