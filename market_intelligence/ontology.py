"""
Product 01: Market Intelligence Engine (V3.6)
Engine 1: Raw Swing Engine
Engine 2: Structure Engine (BOS / CHOCH / Sequence Builder)
Engine 3: Swing Classifier (Classifies Strong/Weak/Protected based on Engine 2 Structure Events)
"""

from typing import List, Tuple, Optional
from market_intelligence.primitives import (
    Candle, RawSwing, ClassifiedSwing, SwingType, SwingScope,
    SwingMagnitude, SwingCharacter, SwingStatus, TrendDirection,
    StructureState, MarketEvent, EventType
)


class MarketOntology:

    def __init__(self, swing_lookback: int = 2):
        self.swing_lookback = swing_lookback

    def detect_raw_swings(self, candles: List[Candle], timeframe: str = "1D") -> List[RawSwing]:
        """ENGINE 1: Geometric Extrema Detection."""
        if len(candles) < (self.swing_lookback * 2 + 1):
            return []

        swings: List[RawSwing] = []
        n = len(candles)

        for i in range(self.swing_lookback, n - self.swing_lookback):
            current = candles[i]
            left = candles[i - self.swing_lookback:i]
            right = candles[i + 1:i + self.swing_lookback + 1]

            if all(current.high > c.high for c in left) and all(current.high > c.high for c in right):
                swings.append(RawSwing(
                    timestamp=current.timestamp,
                    price=current.high,
                    swing_type=SwingType.SWING_HIGH,
                    candle_index=i,
                    timeframe=timeframe
                ))

            if all(current.low < c.low for c in left) and all(current.low < c.low for c in right):
                swings.append(RawSwing(
                    timestamp=current.timestamp,
                    price=current.low,
                    swing_type=SwingType.SWING_LOW,
                    candle_index=i,
                    timeframe=timeframe
                ))

        return swings

    def build_structure(self, candles: List[Candle], raw_swings: List[RawSwing], timeframe: str = "1D") -> Tuple[StructureState, List[MarketEvent]]:
        """
        ENGINE 2: Structure Builder.
        Evaluates candle body closes against raw swings to detect real BOS/CHOCH events and dynamic HH/HL sequences.
        """
        events: List[MarketEvent] = []
        if not candles or not raw_swings:
            structure_state = StructureState(external_trend_seq="NEUTRAL", internal_trend_seq="NEUTRAL")
            structure_state.external_trend = TrendDirection.RANGING
            structure_state.internal_trend = TrendDirection.RANGING
            return structure_state, events

        high_swings = [s for s in raw_swings if s.swing_type == SwingType.SWING_HIGH]
        low_swings = [s for s in raw_swings if s.swing_type == SwingType.SWING_LOW]

        last_high = high_swings[-1] if high_swings else None
        last_low = low_swings[-1] if low_swings else None
        latest_candle = candles[-1]

        last_external_bos = None
        last_external_choch = None

        if last_high and latest_candle.close > last_high.price:
            last_external_bos = MarketEvent(
                timestamp=latest_candle.timestamp,
                timeframe=timeframe,
                symbol="DYNAMIC",
                event_type=EventType.EXTERNAL_BOS,
                price_level=last_high.price,
                metadata={"direction": "BULLISH"}
            )
            events.append(last_external_bos)

        elif last_low and latest_candle.close < last_low.price:
            last_external_choch = MarketEvent(
                timestamp=latest_candle.timestamp,
                timeframe=timeframe,
                symbol="DYNAMIC",
                event_type=EventType.EXTERNAL_CHOCH,
                price_level=last_low.price,
                metadata={"direction": "BEARISH"}
            )
            events.append(last_external_choch)

        high_prices = [s.price for s in high_swings[-3:]]
        low_prices = [s.price for s in low_swings[-3:]]

        is_higher_highs = len(high_prices) >= 2 and high_prices[-1] > high_prices[-2]
        is_higher_lows = len(low_prices) >= 2 and low_prices[-1] > low_prices[-2]

        ext_seq = "HH-HL" if (is_higher_highs and is_higher_lows) else ("LH-LL" if not is_higher_lows else "RANGING")

        structure_state = StructureState(
            external_trend_seq=ext_seq,
            internal_trend_seq=ext_seq,
            last_external_bos=last_external_bos,
            last_external_choch=last_external_choch,
            active_swings=raw_swings,
        )

        if ext_seq == "HH-HL":
            structure_state.external_trend = TrendDirection.BULLISH
            structure_state.internal_trend = TrendDirection.BULLISH
        elif ext_seq == "LH-LL":
            structure_state.external_trend = TrendDirection.BEARISH
            structure_state.internal_trend = TrendDirection.BEARISH
        else:
            structure_state.external_trend = TrendDirection.RANGING
            structure_state.internal_trend = TrendDirection.RANGING

        return structure_state, events

    def evaluate_structure(self, candles: List[Candle], timeframe: str = "1D") -> StructureState:
        raw_swings = self.detect_raw_swings(candles, timeframe=timeframe)
        structure_state, _ = self.build_structure(candles, raw_swings, timeframe=timeframe)
        structure_state.active_swings = raw_swings
        return structure_state

    def classify_swings(self, raw_swings: List[RawSwing], structure_state: StructureState) -> List[ClassifiedSwing]:
        """
        ENGINE 3: Swing Classifier.
        Classifies swings as STRONG/WEAK and PROTECTED/TARGET based on Engine 2 Structure Events!
        """
        classified: List[ClassifiedSwing] = []

        for rs in raw_swings:
            scope = SwingScope.EXTERNAL if rs.candle_index % 2 == 0 else SwingScope.INTERNAL
            magnitude = SwingMagnitude.MAJOR if scope == SwingScope.EXTERNAL else SwingMagnitude.MINOR

            if structure_state.last_external_bos and rs.swing_type == SwingType.SWING_LOW:
                character = SwingCharacter.STRONG
                status = SwingStatus.PROTECTED
            elif structure_state.last_external_choch and rs.swing_type == SwingType.SWING_HIGH:
                character = SwingCharacter.STRONG
                status = SwingStatus.PROTECTED
            else:
                character = SwingCharacter.WEAK
                status = SwingStatus.TARGET

            cs = ClassifiedSwing(
                raw_swing=rs,
                scope=scope,
                magnitude=magnitude,
                character=character,
                status=status
            )

            if cs.character == SwingCharacter.STRONG and cs.raw_swing.swing_type == SwingType.SWING_HIGH:
                structure_state.protected_high = cs
                structure_state.strong_high = cs
            elif cs.character == SwingCharacter.STRONG and cs.raw_swing.swing_type == SwingType.SWING_LOW:
                structure_state.protected_low = cs
                structure_state.strong_low = cs
            elif cs.character == SwingCharacter.WEAK and cs.raw_swing.swing_type == SwingType.SWING_HIGH:
                structure_state.weak_high = cs
            elif cs.character == SwingCharacter.WEAK and cs.raw_swing.swing_type == SwingType.SWING_LOW:
                structure_state.weak_low = cs

            classified.append(cs)

        return classified