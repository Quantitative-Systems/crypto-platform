"""
Product 01: Crypto Platform - Keyzones & Imbalance Engine
Detects Order Blocks (OB) and Fair Value Gaps (FVG) across candlestick series.
"""

from typing import List
from market_intelligence.primitives import (
    Candle, TrendDirection, KeyZone, KeyZoneType
)


class KeyZoneEngine:

    @staticmethod
    def detect_fair_value_gaps(candles: List[Candle]) -> List[KeyZone]:
        """Detects 3-candle Fair Value Gap (FVG) market imbalances."""
        fvgs: List[KeyZone] = []
        total = len(candles)

        if total < 3:
            return fvgs

        for i in range(2, total):
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]

            # Bullish FVG: Low of Candle 3 is greater than High of Candle 1
            if c3.low > c1.high:
                gap_size = c3.low - c1.high
                if gap_size > 0:
                    fvgs.append(KeyZone(
                        zone_id=f"FVG_BULL_{c2.timestamp}",
                        zone_type=KeyZoneType.FAIR_VALUE_GAP,
                        direction=TrendDirection.BULLISH,
                        high=c3.low,
                        low=c1.high,
                        origin_candle_index=i - 1,
                        is_mitigated=False
                    ))

            # Bearish FVG: High of Candle 3 is lower than Low of Candle 1
            elif c3.high < c1.low:
                gap_size = c1.low - c3.high
                if gap_size > 0:
                    fvgs.append(KeyZone(
                        zone_id=f"FVG_BEAR_{c2.timestamp}",
                        zone_type=KeyZoneType.FAIR_VALUE_GAP,
                        direction=TrendDirection.BEARISH,
                        high=c1.low,
                        low=c3.high,
                        origin_candle_index=i - 1,
                        is_mitigated=False
                    ))

        return fvgs

    @staticmethod
    def detect_order_blocks(candles: List[Candle]) -> List[KeyZone]:
        """
        Detects Order Blocks (OB):
        Bullish OB: Last bearish candle before an explosive bullish move.
        Bearish OB: Last bullish candle before an explosive bearish move.
        """
        obs: List[KeyZone] = []
        total = len(candles)

        if total < 4:
            return obs

        for i in range(1, total - 2):
            curr = candles[i]
            next1 = candles[i + 1]
            next2 = candles[i + 2]

            # Bullish OB Check: Red candle followed by strong green expansion
            if curr.close < curr.open:
                expansion = (next2.close - curr.close) / curr.close
                if expansion > 0.02 and next1.close > curr.high:
                    obs.append(KeyZone(
                        zone_id=f"OB_BULL_{curr.timestamp}",
                        zone_type=KeyZoneType.ORDER_BLOCK,
                        direction=TrendDirection.BULLISH,
                        high=curr.high,
                        low=curr.low,
                        origin_candle_index=i,
                        is_mitigated=False
                    ))

            # Bearish OB Check: Green candle followed by strong red contraction
            elif curr.close > curr.open:
                contraction = (curr.close - next2.close) / curr.close
                if contraction > 0.02 and next1.close < curr.low:
                    obs.append(KeyZone(
                        zone_id=f"OB_BEAR_{curr.timestamp}",
                        zone_type=KeyZoneType.ORDER_BLOCK,
                        direction=TrendDirection.BEARISH,
                        high=curr.high,
                        low=curr.low,
                        origin_candle_index=i,
                        is_mitigated=False
                    ))

        return obs
