"""
Product 01: Crypto Platform - KeyZone Detection Engine (V2.1)
Maps Order Blocks (OB) and Fair Value Gaps (FVG) into standardized V2.1 KeyZone objects.
"""

from typing import List
from market_intelligence.primitives import (
    Candle, KeyZone, ZoneType, TrendDirection
)


class KeyZoneEngine:

    @staticmethod
    def detect_keyzones(candles: List[Candle], timeframe: str = "1D") -> List[KeyZone]:
        """Detects Order Blocks and FVGs from candlestick series."""
        if len(candles) < 3:
            return []

        keyzones: List[KeyZone] = []

        # 1. Fair Value Gap (FVG) Detection (3-candle pattern)
        for i in range(2, len(candles)):
            c1, c2, c3 = candles[i - 2], candles[i - 1], candles[i]

            # Bullish FVG: Gap between C1 High and C3 Low
            if c3.low > c1.high:
                keyzones.append(KeyZone(
                    zone_type=ZoneType.BULLISH_FVG,
                    direction=TrendDirection.BULLISH,
                    high=c3.low,
                    low=c1.high,
                    timeframe=timeframe,
                    creation_time=c2.timestamp,
                    is_mitigated=False,
                    strength_score=0.85
                ))

            # Bearish FVG: Gap between C1 Low and C3 High
            elif c3.high < c1.low:
                keyzones.append(KeyZone(
                    zone_type=ZoneType.BEARISH_FVG,
                    direction=TrendDirection.BEARISH,
                    high=c1.low,
                    low=c3.high,
                    timeframe=timeframe,
                    creation_time=c2.timestamp,
                    is_mitigated=False,
                    strength_score=0.85
                ))

        # 2. Order Block (OB) Detection (Last counter candle before expansion)
        if len(candles) >= 4:
            for i in range(1, len(candles) - 1):
                prev_candle = candles[i - 1]
                curr_candle = candles[i]

                # Demand OB: Bearish candle before strong bullish expansion
                if prev_candle.is_bearish and curr_candle.is_bullish and curr_candle.body_range > (prev_candle.range * 1.2):
                    keyzones.append(KeyZone(
                        zone_type=ZoneType.DEMAND_OB,
                        direction=TrendDirection.BULLISH,
                        high=prev_candle.high,
                        low=prev_candle.low,
                        timeframe=timeframe,
                        creation_time=prev_candle.timestamp,
                        is_mitigated=False,
                        strength_score=0.90
                    ))

                # Supply OB: Bullish candle before strong bearish expansion
                elif prev_candle.is_bullish and curr_candle.is_bearish and curr_candle.body_range > (prev_candle.range * 1.2):
                    keyzones.append(KeyZone(
                        zone_type=ZoneType.SUPPLY_OB,
                        direction=TrendDirection.BEARISH,
                        high=prev_candle.high,
                        low=prev_candle.low,
                        timeframe=timeframe,
                        creation_time=prev_candle.timestamp,
                        is_mitigated=False,
                        strength_score=0.90
                    ))

        # Filter out mitigated keyzones by recent price action
        latest_price = candles[-1].close
        for zone in keyzones:
            if zone.direction == TrendDirection.BULLISH and latest_price < zone.low:
                zone.is_mitigated = True
            elif zone.direction == TrendDirection.BEARISH and latest_price > zone.high:
                zone.is_mitigated = True

        return [z for z in keyzones if not z.is_mitigated]