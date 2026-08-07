"""
Product 01: Market Intelligence Engine - Master Domain Contracts (Append-Only Architecture)
Preserves all Engine 01 & 02 primitives and expands SwingStatus enum values.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ============================================================================
# ENGINE 01 CONTRACTS (PRESERVED)
# ============================================================================

class SwingType(Enum):
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"


class SwingStatus(Enum):
    CANDIDATE = "CANDIDATE"      # Peak formed, awaiting right-side confirmation candles
    CONFIRMED = "CONFIRMED"      # Fully confirmed with N right-side closes
    INVALIDATED = "INVALIDATED"  # Overridden by price expansion
    PROTECTED = "PROTECTED"      # Defended anchor point
    TARGET = "TARGET"         # Target liquidity level
    UNASSIGNED = "UNASSIGNED"


class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    NEUTRAL = "NEUTRAL"


class MarketPhase(Enum):
    EXPANSION = "EXPANSION"
    PULLBACK = "PULLBACK"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"
    ACCUMULATION = "ACCUMULATION"
    DISTRIBUTION = "DISTRIBUTION"
    COMPRESSION = "COMPRESSION"


class EventType(Enum):
    EXTERNAL_BOS = "EXTERNAL_BOS"
    INTERNAL_BOS = "INTERNAL_BOS"
    EXTERNAL_CHOCH = "EXTERNAL_CHOCH"
    INTERNAL_CHOCH = "INTERNAL_CHOCH"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    KEYZONE_CREATED = "KEYZONE_CREATED"
    KEYZONE_MITIGATED = "KEYZONE_MITIGATED"


class ZoneType(Enum):
    DEMAND_OB = "DEMAND_OB"
    SUPPLY_OB = "SUPPLY_OB"
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"


class ZoneLifecycle(Enum):
    FRESH = "FRESH"
    ACTIVE = "ACTIVE"
    RETESTED = "RETESTED"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"


class LiquidityType(Enum):
    EQH = "EQH"
    EQL = "EQL"
    BSL = "BSL"
    SSL = "SSL"
    INDUCEMENT = "INDUCEMENT"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def range(self) -> float:
        return max(self.high - self.low, 1e-8)

    @property
    def body_range(self) -> float:
        return abs(self.close - self.open)


@dataclass
class RawSwing:
    swing_id: str
    timestamp: int
    price: float
    swing_type: SwingType
    candle_index: int
    timeframe: str
    status: SwingStatus = SwingStatus.CONFIRMED
    is_equal_extreme: bool = False
    cluster_id: Optional[str] = None
    cluster_member_count: int = 1
    displacement_pct: float = 0.0
    quality_score: float = 100.0
    confidence_score: float = 100.0
    fractal_strength: float = 1.0
    confirmation_candle_index: int = 0
    prev_swing_id: Optional[str] = None
    next_swing_id: Optional[str] = None


@dataclass(frozen=True)
class MarketEvent:
    timestamp: int
    timeframe: str
    symbol: str
    event_type: EventType
    price_level: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# ENGINE 02 CONTRACTS (APPENDED)
# ============================================================================

class SwingScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class SwingMagnitude(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class SwingCharacter(Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"


@dataclass
class ClassifiedSwing:
    raw_swing: RawSwing
    scope: SwingScope
    magnitude: SwingMagnitude
    character: SwingCharacter
    status: SwingStatus
    is_broken: bool = False
    is_swept: bool = False


@dataclass
class StructureState:
    external_trend_seq: str
    internal_trend_seq: str
    last_external_bos: Optional[MarketEvent] = None
    last_internal_bos: Optional[MarketEvent] = None
    last_external_choch: Optional[MarketEvent] = None
    last_internal_choch: Optional[MarketEvent] = None
    protected_high: Optional[ClassifiedSwing] = None
    protected_low: Optional[ClassifiedSwing] = None


# Backward-compatibility alias
SwingPoint = RawSwing

class SequenceLabel(Enum):
    HH = "HH"  # Higher High
    HL = "HL"  # Higher Low
    LH = "LH"  # Lower High
    LL = "LL"  # Lower Low
    EQH = "EQH" # Equal High
    EQL = "EQL" # Equal Low
    UNKNOWN = "UNKNOWN" # First swing in a dataset lacks a predecessor

@dataclass
class SequenceSwing:
    """Engine 02: Wraps a RawSwing with its relational sequence label."""
    raw_swing: RawSwing
    label: SequenceLabel

    class TrendStrength(Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    RANGING = "RANGING"
    WEAK_BEARISH = "WEAK_BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    NEUTRAL = "NEUTRAL"

@dataclass
class SequenceState:
    """Engine 02 Output Container: Wraps swings with fast-access terminal metadata."""
    sequence_swings: List[SequenceSwing]
    latest_high: Optional[SequenceSwing] = None
    latest_low: Optional[SequenceSwing] = None
    latest_higher_high: Optional[SequenceSwing] = None
    latest_higher_low: Optional[SequenceSwing] = None
    total_swings: int = 0

@dataclass
class TrendState:
    """Engine 03 Output Contract: Future-proof structural trend metadata."""
    direction: TrendDirection
    strength: TrendStrength
    confidence: float
    reasoning: str
    latest_high_label: SequenceLabel
    latest_low_label: SequenceLabel
    timestamp: int
    timeframe: str
    source_engine: str = "Engine_03_Trend"
    version: str = "1.0.0"