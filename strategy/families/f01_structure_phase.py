"""Family 01: Structure + Phase.

Uses pure Market Structure / Trend alignment + Phase behavior.
Does NOT require Order Blocks, FVGs, or specific indicator filters.
"""
from __future__ import annotations

from market_model.contracts import MarketState, TrendDirection
from strategy.families.base_family import BaseStrategyFamily


class StructurePhaseFamily(BaseStrategyFamily):
    """Family 01: Structure + Phase."""

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
            family_id="F01_STRUCTURE_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Pure structure: MTF trend should not be strongly opposed to HTF."""
        mtf_trend = mtf_state.structure.external_trend
        if direction == 1 and mtf_trend == TrendDirection.BEARISH:
            # Counter-trend expansion on MTF invalidates
            if mtf_state.phase.is_displaced:
                return False
        elif direction == -1 and mtf_trend == TrendDirection.BULLISH:
            if mtf_state.phase.is_displaced:
                return False
        return True
