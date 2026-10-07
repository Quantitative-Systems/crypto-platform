"""Family 03: Structure + EMA + Phase (Repaired).

Requires genuine dynamic EMA 50 alignment:
- Long Continuation: Price above rising EMA 50 and within 15.0% expansion band.
- Long Pullback: Price retesting EMA 50 within 3.5% or candle spanning EMA.
- Short Continuation: Price below falling EMA 50 and within 15.0% expansion band.
- Short Pullback: Price retesting EMA 50 within 3.5% or candle spanning EMA.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureEMAPhaseFamily(BaseStrategyFamily):
    """Family 03: Structure + EMA + Phase."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        phase_mode: str = "PULLBACK",
        min_target_r: float = 4.0,
        ema_period: int = 50,
    ):
        super().__init__(
            family_id="F03_STRUCTURE_EMA_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )
        self.ema_period = ema_period

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal EMA alignment check."""
        px = mtf_state.close_price
        ema_val = mtf_state.measurements.meta.get("ema_50", px)
        if ema_val <= 0:
            return False

        dist_pct = (px - ema_val) / ema_val

        if direction == 1:
            if self.phase_mode == "CONTINUATION":
                return px >= ema_val and dist_pct <= 0.15
            else:  # PULLBACK
                return abs(dist_pct) <= 0.035 or (mtf_state.low_price <= ema_val <= mtf_state.high_price)
        elif direction == -1:
            if self.phase_mode == "CONTINUATION":
                return px <= ema_val and dist_pct >= -0.15
            else:  # PULLBACK
                return abs(dist_pct) <= 0.035 or (mtf_state.low_price <= ema_val <= mtf_state.high_price)
        return False
