"""Family 06: Structure + Fair Value Gap (FVG) + Phase (Repaired).

Requires genuine causal price interaction with an active, unmitigated MTF Fair Value Gap (FVG):
- Longs: Price actively testing or filling inside unmitigated bullish FVG.
- Shorts: Price actively testing or filling inside unmitigated bearish FVG.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureFVGPhaseFamily(BaseStrategyFamily):
    """Family 06: Structure + FVG + Phase."""

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
            family_id="F06_STRUCTURE_FVG_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal FVG interaction check."""
        fvgs = mtf_state.zones.fair_value_gaps
        if not fvgs:
            return False

        px = mtf_state.close_price
        lo = mtf_state.low_price
        hi = mtf_state.high_price

        if direction == 1:
            return any(
                f.is_bullish
                and not f.is_mitigated
                and (f.low_price * 0.998 <= px <= f.high_price * 1.002 or (lo <= f.high_price and px >= f.low_price))
                for f in fvgs
            )
        elif direction == -1:
            return any(
                not f.is_bullish
                and not f.is_mitigated
                and (f.low_price * 0.998 <= px <= f.high_price * 1.002 or (hi >= f.low_price and px <= f.high_price))
                for f in fvgs
            )
        return False
