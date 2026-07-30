"""
Product 01: Crypto Platform - Liquidity Mapping Engine
Detects Equal Highs (EQH), Equal Lows (EQL), and Liquidity Sweeps.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List
from market_intelligence.primitives import Candle, SwingPoint, SwingType


class LiquidityType(str, Enum):
    EQH = "EQH"  # Equal Highs (Buy-Side Liquidity Pool)
    EQL = "EQL"  # Equal Lows (Sell-Side Liquidity Pool)


@dataclass
class LiquidityPool:
    pool_id: str
    pool_type: LiquidityType
    price_level: float
    touch_count: int
    is_swept: bool = False


@dataclass
class LiquiditySweep:
    pool_id: str
    pool_type: LiquidityType
    sweep_price: float
    candle_index: int
    timestamp: int


class LiquidityEngine:

    @staticmethod
    def detect_equal_levels(swings: List[SwingPoint], tolerance_pct: float = 0.0015) -> List[LiquidityPool]:
        """Maps Equal Highs (EQH) and Equal Lows (EQL) within a tight price percentage variance."""
        pools: List[LiquidityPool] = []
        
        high_swings = [s for s in swings if s.swing_type == SwingType.HIGH]
        low_swings = [s for s in swings if s.swing_type == SwingType.LOW]

        # Map Equal Highs (EQH)
        for i in range(len(high_swings)):
            for j in range(i + 1, len(high_swings)):
                s1, s2 = high_swings[i], high_swings[j]
                diff_pct = abs(s1.price - s2.price) / s1.price
                if diff_pct <= tolerance_pct:
                    avg_price = (s1.price + s2.price) / 2.0
                    pools.append(LiquidityPool(
                        pool_id=f"EQH_{s1.index}_{s2.index}",
                        pool_type=LiquidityType.EQH,
                        price_level=avg_price,
                        touch_count=2
                    ))

        # Map Equal Lows (EQL)
        for i in range(len(low_swings)):
            for j in range(i + 1, len(low_swings)):
                s1, s2 = low_swings[i], low_swings[j]
                diff_pct = abs(s1.price - s2.price) / s1.price
                if diff_pct <= tolerance_pct:
                    avg_price = (s1.price + s2.price) / 2.0
                    pools.append(LiquidityPool(
                        pool_id=f"EQL_{s1.index}_{s2.index}",
                        pool_type=LiquidityType.EQL,
                        price_level=avg_price,
                        touch_count=2
                    ))

        return pools

    @staticmethod
    def detect_sweeps(candles: List[Candle], pools: List[LiquidityPool]) -> List[LiquiditySweep]:
        """
        Detects Liquidity Sweeps:
        - EQH Sweep: High pierces EQH level, but Close stays BELOW EQH.
        - EQL Sweep: Low pierces EQL level, but Close stays ABOVE EQL.
        """
        sweeps: List[LiquiditySweep] = []

        for pool in pools:
            if pool.is_swept:
                continue

            for i, candle in enumerate(candles):
                # Check Buy-Side Liquidity Sweep (EQH)
                if pool.pool_type == LiquidityType.EQH:
                    if candle.high > pool.price_level and candle.close < pool.price_level:
                        pool.is_swept = True
                        sweeps.append(LiquiditySweep(
                            pool_id=pool.pool_id,
                            pool_type=pool.pool_type,
                            sweep_price=candle.high,
                            candle_index=i,
                            timestamp=candle.timestamp
                        ))
                        break

                # Check Sell-Side Liquidity Sweep (EQL)
                elif pool.pool_type == LiquidityType.EQL:
                    if candle.low < pool.price_level and candle.close > pool.price_level:
                        pool.is_swept = True
                        sweeps.append(LiquiditySweep(
                            pool_id=pool.pool_id,
                            pool_type=pool.pool_type,
                            sweep_price=candle.low,
                            candle_index=i,
                            timestamp=candle.timestamp
                        ))
                        break

        return sweeps
