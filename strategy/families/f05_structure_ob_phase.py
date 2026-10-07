"""Family 05: Structure + Order Block + Phase (Repaired).

Requires genuine causal price interaction with an active, unmitigated MTF Order Block (OB):
- Longs: Current price or candle range touching/inside unmitigated bullish OB.
- Shorts: Current price or candle range touching/inside unmitigated bearish OB.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureOBPhaseFamily(BaseStrategyFamily):
    """Family 05: Structure + OB + Phase."""

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
            family_id="F05_STRUCTURE_OB_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal Order Block interaction check."""
        obs = mtf_state.zones.order_blocks
        if not obs:
            return False

        px = mtf_state.close_price
        lo = mtf_state.low_price
        hi = mtf_state.high_price

        if direction == 1:
            return any(
                ob.is_bullish
                and not ob.is_mitigated
                and (ob.low_price * 0.998 <= px <= ob.high_price * 1.01 or (lo <= ob.high_price and px >= ob.low_price))
                for ob in obs
            )
        elif direction == -1:
            return any(
                not ob.is_bullish
                and not ob.is_mitigated
                and (ob.low_price * 0.99 <= px <= ob.high_price * 1.002 or (hi >= ob.low_price and px <= ob.high_price))
                for ob in obs
            )
        return False
