"""
Product 01 — Market Language
Sub-System 1 — Market Structure
Foundational domain primitives and data contracts.

Design principles:
- Pure domain objects only.
- No trading/execution logic.
- Explicit confirmation timing for backtest safety.
- Explicit internal/external scope.
- Explicit structural roles.
- Explicit event/state contracts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class SwingType(Enum):
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    HIGH = "SWING_HIGH"
    LOW = "SWING_LOW"


class SwingScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class SwingStatus(Enum):
    DEVELOPING = "DEVELOPING"
    CONFIRMED = "CONFIRMED"
    PROTECTED = "PROTECTED"
    STRONG = "STRONG"
    WEAK = "WEAK"
    BROKEN = "BROKEN"


class SequenceLabel(Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    EQH = "EQH"
    EQL = "EQL"
    UNKNOWN = "UNKNOWN"


class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    NEUTRAL = "NEUTRAL"


class StructuralRole(Enum):
    NONE = "NONE"
    PROTECTED_HIGH = "PROTECTED_HIGH"
    PROTECTED_LOW = "PROTECTED_LOW"
    WEAK_HIGH = "WEAK_HIGH"
    WEAK_LOW = "WEAK_LOW"


class EventType(Enum):
    EXTERNAL_BOS = "EXTERNAL_BOS"
    EXTERNAL_CHOCH = "EXTERNAL_CHOCH"

    INTERNAL_BOS = "INTERNAL_BOS"
    INTERNAL_CHOCH = "INTERNAL_CHOCH"

    MSS = "MSS"

    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    INDUCEMENT = "INDUCEMENT"

    FAILED_BOS = "FAILED_BOS"


class LiquiditySide(Enum):
    BSL = "BSL"
    SSL = "SSL"


class LiquidityPoolType(Enum):
    EQH = "EQH"
    EQL = "EQL"


class ZoneType(Enum):
    BULLISH_OB = "BULLISH_OB"
    BEARISH_OB = "BEARISH_OB"
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"
    BREAKER_BLOCK = "BREAKER_BLOCK"
    MITIGATION_BLOCK = "MITIGATION_BLOCK"


class MarketPhase(Enum):
    ACCUMULATION = "ACCUMULATION"
    EXPANSION = "EXPANSION"
    PULLBACK = "PULLBACK"
    MANIPULATION = "MANIPULATION"
    CONTINUATION = "CONTINUATION"
    DISTRIBUTION = "DISTRIBUTION"
    REVERSAL = "REVERSAL"
    COMPRESSION = "COMPRESSION"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class RawSwing:
    swing_id: str
    timestamp: int
    price: float

    swing_type: SwingType

    # Candle where the actual extreme happened.
    candle_index: int

    # First candle where the swing becomes knowable.
    confirmation_timestamp: int
    confirmation_index: int

    timeframe: str = "1H"

    status: SwingStatus = SwingStatus.CONFIRMED
    scope: SwingScope = SwingScope.INTERNAL

    # Index of the structural parent, if one exists.
    parent_swing_id: Optional[str] = None


@dataclass
class SequenceSwing:
    raw_swing: RawSwing
    label: SequenceLabel

    role: StructuralRole = StructuralRole.NONE
    scope: SwingScope = SwingScope.INTERNAL

    is_protected: bool = False
    is_strong: bool = False
    is_weak: bool = False


@dataclass
class SequenceState:
    sequence_swings: List[SequenceSwing]

    latest_high: Optional[SequenceSwing] = None
    previous_high: Optional[SequenceSwing] = None

    latest_low: Optional[SequenceSwing] = None
    previous_low: Optional[SequenceSwing] = None

    latest_external_high: Optional[SequenceSwing] = None
    latest_external_low: Optional[SequenceSwing] = None

    latest_internal_high: Optional[SequenceSwing] = None
    latest_internal_low: Optional[SequenceSwing] = None

    total_swings: int = 0


@dataclass
class DealingRange:
    high_swing: Optional[SequenceSwing] = None
    low_swing: Optional[SequenceSwing] = None

    equilibrium_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0


@dataclass
class EQHLiquidityPool:
    pool_id: str

    pool_type: LiquidityPoolType

    price_level: float

    swings: List[SequenceSwing]

    tolerance_pct: float = 0.0005

    is_swept: bool = False

    swept_timestamp: Optional[int] = None


@dataclass
class MarketEvent:
    timestamp: int
    timeframe: str
    symbol: str

    event_type: EventType

    price_level: float

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructureEvent:
    timestamp: int
    event_type: EventType
    price_level: float
    broken_swing_id: str
    direction: str
    candle_index: int
    confirmation: str = "BODY_CLOSE"
    structural_epoch: int = 0


@dataclass
class StructureState:
    """
    Current structural snapshot.

    This object represents the structure known at the current processing point.
    """

    external_trend: TrendDirection = TrendDirection.NEUTRAL
    internal_trend: TrendDirection = TrendDirection.NEUTRAL

    sequence_swings: List[SequenceSwing] = field(default_factory=list)
    external_swings: List[SequenceSwing] = field(default_factory=list)
    internal_swings: List[SequenceSwing] = field(default_factory=list)

    protected_high: Optional[SequenceSwing] = None
    protected_low: Optional[SequenceSwing] = None

    weak_high: Optional[SequenceSwing] = None
    weak_low: Optional[SequenceSwing] = None

    dealing_range: Optional[DealingRange] = None
    events: List[StructureEvent] = field(default_factory=list)

    last_event: Optional[MarketEvent] = None
    broken_protected_swing_id: Optional[str] = None
    structural_epoch: int = 0


@dataclass
class MarketStatePayload:
    symbol: str
    timeframe: str
    timestamp: int

    current_price: float

    current_candle: Optional[Candle]

    events: List[MarketEvent]

    swings: List[RawSwing]

    structure_state: StructureState

    liquidity_pools: List[EQHLiquidityPool]

    keyzones: List["KeyZone"]

    phase_state: Optional[MarketPhase]

    trend_state: Optional[TrendDirection]

    valuation_state: Optional[str] = "EQUILIBRIUM"

    scorecard: Optional[Dict[str, Any]] = None

    metadata: Optional[Dict[str, Any]] = None


@dataclass
class KeyZone:
    """
    Reserved for Product 01 — Sub-System 2.
    """

    zone_id: str

    zone_type: ZoneType

    direction: TrendDirection

    high: float
    low: float

    timeframe: str

    creation_timestamp: int

    is_mitigated: bool = False

    strength_score: float = 1.0
