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
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    PROTECTED = "PROTECTED"
    TARGET = "TARGET"
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
    BOS = "BOS"
    CHOCH = "CHOCH"
    SWEEP = "SWEEP"


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


class SwingScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class SwingMagnitude(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class SwingCharacter(Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"


class SequenceLabel(Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    EQH = "EQH"
    EQL = "EQL"
    UNKNOWN = "UNKNOWN"


class TrendStrength(Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    RANGING = "RANGING"
    WEAK_BEARISH = "WEAK_BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    NEUTRAL = "NEUTRAL"


class SessionType(Enum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OFF_HOURS = "OFF_HOURS"


class VolatilityRegime(Enum):
    NORMAL = "NORMAL"
    EXPANSION = "EXPANSION"
    COMPRESSION = "COMPRESSION"
    HIGH_VOLATILITY_SHOCK = "HIGH_VOLATILITY_SHOCK"


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
    swing_id: str = ""
    timestamp: int = 0
    price: float = 0.0
    swing_type: SwingType = SwingType.SWING_HIGH
    candle_index: int = 0
    timeframe: str = "1D"
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
    external_trend: Optional[TrendDirection] = None
    internal_trend: Optional[TrendDirection] = None
    strong_high: Optional[ClassifiedSwing] = None
    strong_low: Optional[ClassifiedSwing] = None
    weak_high: Optional[ClassifiedSwing] = None
    weak_low: Optional[ClassifiedSwing] = None
    active_swings: List[RawSwing] = field(default_factory=list)


@dataclass
class SequenceSwing:
    """Engine 02: Wraps a RawSwing with its relational sequence label."""
    raw_swing: RawSwing
    label: SequenceLabel


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
    latest_high_label: Optional[SequenceLabel]
    latest_low_label: Optional[SequenceLabel]
    timestamp: int
    timeframe: str
    source_engine: str = "Engine_03_Trend"
    version: str = "1.0.0"
    external_trend: Optional[TrendDirection] = None
    internal_trend: Optional[TrendDirection] = None
    trend_strength: float = 0.0
    trend_age_bars: int = 0
    is_aligned: bool = True


@dataclass
class PhaseState:
    current_phase: MarketPhase
    expected_next_phase: MarketPhase
    bars_in_phase: int


@dataclass
class ValuationState:
    range_high: float
    range_low: float
    equilibrium: float
    premium_boundary: float
    discount_boundary: float
    current_distance_from_eq: float


@dataclass
class ValidationScorecard:
    structure_score: float
    liquidity_score: float
    zone_score: float
    trend_score: float
    phase_score: float
    validation_score: float

    @property
    def overall_score(self) -> float:
        return (self.structure_score + self.liquidity_score + self.zone_score + self.trend_score + self.phase_score) / 5.0


@dataclass
class EngineMetadata:
    engine_version: str
    processing_time_ms: float
    confidence: float


@dataclass
class SessionState:
    active_session: SessionType
    session_high: float
    session_low: float
    is_killzone: bool


@dataclass
class VolatilityState:
    atr_value: float
    regime: VolatilityRegime
    relative_volume_ratio: float


@dataclass
class KeyZone:
    zone_type: ZoneType
    direction: TrendDirection
    high: float
    low: float
    timeframe: str
    creation_time: int
    is_mitigated: bool = False
    strength_score: float = 0.0


@dataclass
class LiquidityPool:
    liquidity_type: LiquidityType
    direction: TrendDirection
    price_level: float
    high_bound: float
    low_bound: float
    timeframe: str
    creation_time: int
    is_swept: bool = False
    sweep_count: int = 0


@dataclass
class StructureEvent:
    event_type: EventType
    direction: TrendDirection
    price_level: float
    timestamp: int
    timeframe: str


@dataclass
class ZoneState:
    active_keyzones: List[KeyZone] = field(default_factory=list)


@dataclass
class MarketStatePayload:
    symbol: str
    timeframe: str
    timestamp: int
    current_price: float
    current_candle: Candle
    events: List[MarketEvent]
    swings: List[ClassifiedSwing]
    structure_state: StructureState
    liquidity_pools: List[LiquidityPool]
    keyzones: List[KeyZone]
    phase_state: PhaseState
    trend_state: TrendState
    valuation_state: ValuationState
    scorecard: ValidationScorecard
    metadata: EngineMetadata
    zone_state: ZoneState = field(default_factory=ZoneState)

    @property
    def trend(self) -> TrendDirection:
        return self.trend_state.direction if self.trend_state else TrendDirection.NEUTRAL

    @property
    def last_event(self) -> Optional[MarketEvent]:
        return self.events[-1] if self.events else None

    @property
    def active_keyzones(self) -> List[KeyZone]:
        return self.zone_state.active_keyzones if self.zone_state else self.keyzones

    @property
    def protected_high(self) -> Optional[float]:
        return self.structure_state.protected_high.raw_swing.price if self.structure_state and self.structure_state.protected_high else None

    @property
    def protected_low(self) -> Optional[float]:
        return self.structure_state.protected_low.raw_swing.price if self.structure_state and self.structure_state.protected_low else None


# Backward-compatibility alias
SwingPoint = RawSwing