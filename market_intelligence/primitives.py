"""
Product 01: Crypto Platform - Market Intelligence Primitives
Defines pure dataclasses for price action data contracts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    NEUTRAL = "NEUTRAL"


class EventType(str, Enum):
    BOS = "BOS"      # Break of Structure (Continuation)
    CHOCH = "CHOCH"  # Change of Character (Reversal)


class SwingType(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class KeyZoneType(str, Enum):
    ORDER_BLOCK = "ORDER_BLOCK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"


class MarketPhase(str, Enum):
    PULLBACK = "PULLBACK"
    CONTINUATION = "CONTINUATION"
    EXPANSION = "EXPANSION"
    REVERSAL = "REVERSAL"
    RANGE = "RANGE"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class SwingPoint:
    index: int
    price: float
    swing_type: SwingType
    timestamp: int


@dataclass
class StructureEvent:
    event_type: EventType
    direction: TrendDirection
    broken_price_level: float
    candle_index: int
    timestamp: int


@dataclass
class KeyZone:
    zone_id: str
    zone_type: KeyZoneType
    direction: TrendDirection
    high: float
    low: float
    origin_candle_index: int
    is_mitigated: bool = False


@dataclass
class MarketStatePayload:
    symbol: str
    timeframe: str
    trend: TrendDirection
    protected_high: Optional[float]
    protected_low: Optional[float]
    last_event: Optional[StructureEvent]
    active_swings: List[SwingPoint] = field(default_factory=list)
    active_keyzones: List[KeyZone] = field(default_factory=list)
    active_liquidity_pools: List[any] = field(default_factory=list)
    active_liquidity_sweeps: List[any] = field(default_factory=list)
    market_phase: MarketPhase = MarketPhase.RANGE
