"""
Product 01: Crypto Platform - Liquidity Pool & Sweep Engine (V2.1)
Maps Equal Highs (EQH), Equal Lows (EQL), and Liquidity Sweep Events.
"""

from typing import List, Optional
from market_intelligence.primitives import (
    Candle, LiquidityPool, LiquidityType, StructureEvent, EventType, TrendDirection
)


class LiquidityEngine:

    @staticmethod
    def detect_pools(candles: List[Candle], timeframe: str = "1D", tolerance_pct: float = 0.001) -> List[LiquidityPool]:
        """Detects Equal Highs (EQH) and Equal Lows (EQL) within tolerance."""
        if len(candles) < 10:
            return []

        pools: List[LiquidityPool] = []
        n = len(candles)

        for i in range(n - 10, n - 1):
            for j in range(i + 1, n):
                c1, c2 = candles[i], candles[j]

                # Equal Highs (EQH)
                if abs(c1.high - c2.high) / c1.high <= tolerance_pct:
                    pools.append(LiquidityPool(
                        liquidity_type=LiquidityType.EQH,
                        direction=TrendDirection.BEARISH,
                        price_level=max(c1.high, c2.high),
                        high_bound=max(c1.high, c2.high) * 1.001,
                        low_bound=min(c1.high, c2.high) * 0.999,
                        timeframe=timeframe,
                        creation_time=c2.timestamp
                    ))

                # Equal Lows (EQL)
                if abs(c1.low - c2.low) / c1.low <= tolerance_pct:
                    pools.append(LiquidityPool(
                        liquidity_type=LiquidityType.EQL,
                        direction=TrendDirection.BULLISH,
                        price_level=min(c1.low, c2.low),
                        high_bound=max(c1.low, c2.low) * 1.001,
                        low_bound=min(c1.low, c2.low) * 0.999,
                        timeframe=timeframe,
                        creation_time=c2.timestamp
                    ))

        return pools

    @staticmethod
    def detect_sweeps(candles: List[Candle], pools: List[LiquidityPool], timeframe: str = "1D") -> Optional[StructureEvent]:
        """Detects if recent candle pierced a liquidity pool and closed back inside."""
        if not candles or not pools:
            return None

        latest = candles[-1]

        for pool in pools:
            if pool.is_swept:
                continue

            # Bullish Sweep of EQL: Low pierces pool low, close stays above
            if pool.direction == TrendDirection.BULLISH and latest.low <= pool.price_level and latest.close > pool.price_level:
                pool.is_swept = True
                pool.sweep_count += 1
                return StructureEvent(
                    event_type=EventType.SWEEP,
                    direction=TrendDirection.BULLISH,
                    price_level=pool.price_level,
                    timestamp=latest.timestamp,
                    timeframe=timeframe
                )

            # Bearish Sweep of EQH: High pierces pool high, close stays below
            elif pool.direction == TrendDirection.BEARISH and latest.high >= pool.price_level and latest.close < pool.price_level:
                pool.is_swept = True
                pool.sweep_count += 1
                return StructureEvent(
                    event_type=EventType.SWEEP,
                    direction=TrendDirection.BEARISH,
                    price_level=pool.price_level,
                    timestamp=latest.timestamp,
                    timeframe=timeframe
                )

        return None