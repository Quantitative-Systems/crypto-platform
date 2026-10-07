"""Key Zones & Levels Coordinator Engine.

Composes specialized causal engines for:
- Fair Value Gaps (FVG)
- Order Blocks (OB)
- Liquidity Pools (BSL, SSL, EQH, EQL)
- Premium / Discount / Equilibrium Zones
- Support and Resistance
"""
from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from market_model.contracts import (
    KeyZone,
    LiquidityPool,
    StructureSnapshot,
    ZonesSnapshot,
)
from market_model.key_zones_levels.fair_value_gaps.fvg_engine import FVGEngine
from market_model.key_zones_levels.order_blocks.order_block_engine import OrderBlockEngine
from market_model.key_zones_levels.liquidity.liquidity_engine import LiquidityEngine
from market_model.key_zones_levels.premium_discount.premium_discount_engine import PremiumDiscountEngine
from market_model.key_zones_levels.support_resistance.support_resistance_engine import SupportResistanceEngine


class KeyZonesEngine:
    """Causal coordinator for detecting Order Blocks, FVGs, Liquidity, S/R, and Premium/Discount."""

    def __init__(
        self,
        fvg_min_bps: float = 5.0,
        eq_high_low_tolerance_bps: float = 15.0,
        max_active_zones: int = 20,
    ):
        self.fvg_min_bps = fvg_min_bps
        self.eq_high_low_tolerance_bps = eq_high_low_tolerance_bps
        self.max_active_zones = max_active_zones

        self.fvg_engine = FVGEngine(fvg_min_bps=fvg_min_bps, max_active_zones=max_active_zones)
        self.ob_engine = OrderBlockEngine(max_active_zones=max_active_zones)
        self.liq_engine = LiquidityEngine(tolerance_bps=eq_high_low_tolerance_bps)
        self.pd_engine = PremiumDiscountEngine(equilibrium_buffer_pct=0.05)
        self.sr_engine = SupportResistanceEngine(zone_buffer_bps=10.0)

    def detect_fair_value_gaps(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, timestamps: np.ndarray
    ) -> List[KeyZone]:
        """Detect Fair Value Gaps (FVG / Imbalances) and track mitigation."""
        return self.fvg_engine.detect_fair_value_gaps(highs, lows, closes, timestamps)

    def detect_order_blocks(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        structure: StructureSnapshot,
    ) -> List[KeyZone]:
        """Detect Order Blocks associated with displacement / structure breaks."""
        return self.ob_engine.detect_order_blocks(opens, highs, lows, closes, timestamps, structure)

    def detect_liquidity_pools(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        timestamps: np.ndarray,
        structure: StructureSnapshot,
    ) -> List[LiquidityPool]:
        """Identify Equal Highs/Lows and Buy-side/Sell-side liquidity pools."""
        return self.liq_engine.detect_liquidity_pools(highs, lows, timestamps, structure)

    def compute_zones(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        structure: Optional[StructureSnapshot] = None,
    ) -> ZonesSnapshot:
        """Compute complete ZonesSnapshot causally up to current bar."""
        if len(closes) == 0:
            return ZonesSnapshot()

        struct = structure or StructureSnapshot()
        fvgs = self.detect_fair_value_gaps(highs, lows, closes, timestamps)
        obs = self.detect_order_blocks(opens, highs, lows, closes, timestamps, struct)
        liq = self.detect_liquidity_pools(highs, lows, timestamps, struct)
        range_h, range_l, eq_price, pd_zone, fibs = self.pd_engine.compute_dealing_range(
            highs, lows, closes, struct
        )
        sr_zones = self.sr_engine.detect_support_resistance(highs, lows, closes, timestamps, struct)

        return ZonesSnapshot(
            order_blocks=obs,
            fair_value_gaps=fvgs,
            liquidity_pools=liq,
            support_resistance=sr_zones,
            premium_discount_zone=pd_zone,
            equilibrium_price=eq_price,
            fibonacci_levels=fibs,
            previous_high=range_h,
            previous_low=range_l,
        )
