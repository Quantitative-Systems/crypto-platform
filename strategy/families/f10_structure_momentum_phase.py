"""Family 10: Structure + Momentum + Phase (Repaired).

Requires genuine causal momentum expansion and volume confirmation:
- Longs: RSI in active bullish momentum regime (52.0 - 75.0) AND Volume Ratio >= 1.05.
- Shorts: RSI in active bearish momentum regime (25.0 - 48.0) AND Volume Ratio >= 1.05.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureMomentumPhaseFamily(BaseStrategyFamily):
    """Family 10: Structure + Momentum + Phase."""

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
            family_id="F10_STRUCTURE_MOMENTUM_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal momentum and volume expansion check."""
        meas = mtf_state.measurements
        if direction == 1:
            return 52.0 <= meas.rsi <= 75.0 and meas.volume_sma_ratio >= 1.05
        elif direction == -1:
            return 25.0 <= meas.rsi <= 48.0 and meas.volume_sma_ratio >= 1.05
        return False
