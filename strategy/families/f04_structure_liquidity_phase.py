"""Family 04: Structure + Liquidity + Phase (Repaired).

Requires genuine causal interaction with key institutional liquidity pools:
- Longs: Sell-Side Liquidity (SSL) or Equal Lows (EQL) swept (pool flagged swept or candle dipped below and closed above).
- Shorts: Buy-Side Liquidity (BSL) or Equal Highs (EQH) swept (pool flagged swept or candle pierced above and closed below).
"""
from __future__ import annotations

from market_model.contracts import LiquidityType, MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureLiquidityPhaseFamily(BaseStrategyFamily):
    """Family 04: Structure + Liquidity + Phase."""

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
            family_id="F04_STRUCTURE_LIQUIDITY_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal liquidity pool interaction check."""
        pools = mtf_state.zones.liquidity_pools
        if not pools:
            return False

        px = mtf_state.close_price
        lo = mtf_state.low_price
        hi = mtf_state.high_price

        if direction == 1:
            return any(
                p.liquidity_type in (LiquidityType.SELLSIDE_LIQUIDITY, LiquidityType.EQUAL_LOWS)
                and (p.is_swept or (lo < p.price_level and px >= p.price_level * 0.995))
                for p in pools
            )
        elif direction == -1:
            return any(
                p.liquidity_type in (LiquidityType.BUYSIDE_LIQUIDITY, LiquidityType.EQUAL_HIGHS)
                and (p.is_swept or (hi > p.price_level and px <= p.price_level * 1.005))
                for p in pools
            )
        return False
