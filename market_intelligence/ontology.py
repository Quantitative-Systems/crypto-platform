"""
Product 01: Crypto Platform - Universal Market Ontology Engine
Applies deterministic price action rules: Fractals -> BOS/CHOCH -> Protected Anchors.
"""

from typing import List, Optional
from market_intelligence.primitives import (
    Candle, TrendDirection, SwingPoint, SwingType,
    StructureEvent, EventType, MarketStatePayload
)


class UniversalOntologyEngine:

    def __init__(self, swing_lookback: int = 2):
        self.swing_lookback = swing_lookback

    def detect_swings(self, candles: List[Candle]) -> List[SwingPoint]:
        """Detects fractal Swing Highs and Swing Lows using N-left, N-right rule."""
        swings: List[SwingPoint] = []
        n = self.swing_lookback
        total = len(candles)

        if total < (2 * n + 1):
            return swings

        for i in range(n, total - n):
            curr = candles[i]

            # Swing High Check
            is_high = all(curr.high > candles[i - j].high and curr.high > candles[i + j].high for j in range(1, n + 1))
            if is_high:
                swings.append(SwingPoint(index=i, price=curr.high, swing_type=SwingType.HIGH, timestamp=curr.timestamp))

            # Swing Low Check
            is_low = all(curr.low < candles[i - j].low and curr.low < candles[i + j].low for j in range(1, n + 1))
            if is_low:
                swings.append(SwingPoint(index=i, price=curr.low, swing_type=SwingType.LOW, timestamp=curr.timestamp))

        return swings

    def evaluate_structure(self, candles: List[Candle], symbol: str = "BTC/USDT", timeframe: str = "1D") -> MarketStatePayload:
        """Parses candlestick series to output a deterministic MarketStatePayload."""
        if not candles or len(candles) < 5:
            return MarketStatePayload(
                symbol=symbol, timeframe=timeframe, trend=TrendDirection.NEUTRAL,
                protected_high=None, protected_low=None, last_event=None
            )

        swings = self.detect_swings(candles)
        
        current_trend = TrendDirection.NEUTRAL
        last_event: Optional[StructureEvent] = None
        protected_high: Optional[float] = None
        protected_low: Optional[float] = None

        last_swing_high: Optional[SwingPoint] = None
        last_swing_low: Optional[SwingPoint] = None

        # Sequential Structure Analysis
        for i, candle in enumerate(candles):
            available_swings = [s for s in swings if s.index < i]
            swing_highs = [s for s in available_swings if s.swing_type == SwingType.HIGH]
            swing_lows = [s for s in available_swings if s.swing_type == SwingType.LOW]

            if swing_highs:
                last_swing_high = swing_highs[-1]
            if swing_lows:
                last_swing_low = swing_lows[-1]

            # Bullish Break Check (Price Close > Last Swing High)
            if last_swing_high and candle.close > last_swing_high.price:
                event_type = EventType.BOS if current_trend == TrendDirection.BULLISH else EventType.CHOCH
                current_trend = TrendDirection.BULLISH
                last_event = StructureEvent(
                    event_type=event_type, direction=TrendDirection.BULLISH,
                    broken_price_level=last_swing_high.price, candle_index=i, timestamp=candle.timestamp
                )
                if swing_lows:
                    protected_low = swing_lows[-1].price
                last_swing_high = None

            # Bearish Break Check (Price Close < Last Swing Low)
            elif last_swing_low and candle.close < last_swing_low.price:
                event_type = EventType.BOS if current_trend == TrendDirection.BEARISH else EventType.CHOCH
                current_trend = TrendDirection.BEARISH
                last_event = StructureEvent(
                    event_type=event_type, direction=TrendDirection.BEARISH,
                    broken_price_level=last_swing_low.price, candle_index=i, timestamp=candle.timestamp
                )
                if swing_highs:
                    protected_high = swing_highs[-1].price
                last_swing_low = None

        return MarketStatePayload(
            symbol=symbol, timeframe=timeframe, trend=current_trend,
            protected_high=protected_high, protected_low=protected_low,
            last_event=last_event, active_swings=swings[-10:] if swings else []
        )
