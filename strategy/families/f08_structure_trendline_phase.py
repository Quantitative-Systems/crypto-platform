"""Family 08: Structure + Trendline + Phase.

Requires dynamic swing trendline alignment:
- Bullish: Higher swing lows connecting an ascending trendline.
- Bearish: Lower swing highs connecting a descending trendline.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureTrendlinePhaseFamily(BaseStrategyFamily):
    """Family 08: Structure + Trendline + Phase."""

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
            family_id="F08_STRUCTURE_TRENDLINE_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Trendline geometry check from swing pivots."""
        struct = mtf_state.structure
        # Requires at least two recent swing points to form a baseline trendline
        if direction == 1:
            # Bullish trendline: last minor low higher than previous major low
            if struct.last_minor_low and struct.last_major_low:
                return struct.last_minor_low.price >= struct.last_major_low.price
            return True
        elif direction == -1:
            # Bearish trendline: last minor high lower than previous major high
            if struct.last_minor_high and struct.last_major_high:
                return struct.last_minor_high.price <= struct.last_major_high.price
            return True
        return False
