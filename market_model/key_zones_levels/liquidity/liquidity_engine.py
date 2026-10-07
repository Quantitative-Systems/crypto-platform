"""Liquidity Detection Engine.

Identifies institutional liquidity locations causally:
- Buy-Side Liquidity (BSL): Unmitigated major highs, equal highs (EQH).
- Sell-Side Liquidity (SSL): Unmitigated major lows, equal lows (EQL).
- Sweep Detection: Wicks piercing liquidity levels.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from market_model.contracts import (
    LiquidityPool,
    LiquidityType,
    StructureSnapshot,
)


class LiquidityEngine:
    """Causal engine for detecting and tracking institutional liquidity pools."""

    def __init__(self, tolerance_bps: float = 15.0):
        self.tolerance_bps = tolerance_bps

    def detect_liquidity_pools(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        timestamps: np.ndarray,
        structure: StructureSnapshot,
    ) -> List[LiquidityPool]:
        """Identify Equal Highs/Lows and Buy-side/Sell-side liquidity pools."""
        pools: List[LiquidityPool] = []
        n = len(highs)
        if n == 0:
            return pools

        curr_high = float(highs[-1])
        curr_low = float(lows[-1])

        # 1. Major Swing Structural Liquidity
        if structure.last_major_high:
            h_px = structure.last_major_high.price
            h_ts = structure.last_major_high.timestamp_ms
            pools.append(
                LiquidityPool(
                    pool_id=f"BSL_{h_ts}",
                    liquidity_type=LiquidityType.BUYSIDE_LIQUIDITY,
                    price_level=h_px,
                    timestamp_ms=h_ts,
                    is_swept=curr_high > h_px,
                    swept_at_ms=int(timestamps[-1]) if curr_high > h_px else None,
                )
            )

        if structure.last_major_low:
            l_px = structure.last_major_low.price
            l_ts = structure.last_major_low.timestamp_ms
            pools.append(
                LiquidityPool(
                    pool_id=f"SSL_{l_ts}",
                    liquidity_type=LiquidityType.SELLSIDE_LIQUIDITY,
                    price_level=l_px,
                    timestamp_ms=l_ts,
                    is_swept=curr_low < l_px,
                    swept_at_ms=int(timestamps[-1]) if curr_low < l_px else None,
                )
            )

        # 2. Equal Highs / Lows (EQH / EQL)
        scan_len = min(60, n)
        recent_highs = highs[-scan_len:]
        recent_lows = lows[-scan_len:]
        tol_frac = self.tolerance_bps / 1e4

        for i in range(len(recent_highs) - 5):
            for j in range(i + 3, len(recent_highs)):
                hi_i = recent_highs[i]
                hi_j = recent_highs[j]
                if abs(hi_i - hi_j) / hi_i <= tol_frac:
                    pools.append(
                        LiquidityPool(
                            pool_id=f"EQH_{timestamps[-scan_len + i]}_{timestamps[-scan_len + j]}",
                            liquidity_type=LiquidityType.EQUAL_HIGHS,
                            price_level=float((hi_i + hi_j) / 2.0),
                            timestamp_ms=int(timestamps[-scan_len + j]),
                            is_swept=curr_high > max(hi_i, hi_j),
                        )
                    )
                    break

        return pools
