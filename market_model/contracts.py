"""Canonical Market State Contracts & Domain Definitions.

This module defines the unified, deterministic, serializable MarketState contract
representing a complete snapshot of market structure, key zones, market phases,
and measurements for a given (symbol, timestamp, timeframe).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGE = "RANGE"
    NEUTRAL = "NEUTRAL"
    TRANSITIONAL = "TRANSITIONAL"


class MarketPhaseType(str, Enum):
    PULLBACK = "PULLBACK"
    CONTINUATION = "CONTINUATION"
    CONSOLIDATION = "CONSOLIDATION"
    UNCERTAIN = "UNCERTAIN"


class StructuralBreakType(str, Enum):
    BOS_BULLISH = "BOS_BULLISH"
    BOS_BEARISH = "BOS_BEARISH"
    CHOCH_BULLISH = "CHOCH_BULLISH"
    CHOCH_BEARISH = "CHOCH_BEARISH"
    MSS_BULLISH = "MSS_BULLISH"
    MSS_BEARISH = "MSS_BEARISH"
    FAILED_BREAK = "FAILED_BREAK"


class LiquidityType(str, Enum):
    EQUAL_HIGHS = "EQUAL_HIGHS"
    EQUAL_LOWS = "EQUAL_LOWS"
    BUYSIDE_LIQUIDITY = "BUYSIDE_LIQUIDITY"
    SELLSIDE_LIQUIDITY = "SELLSIDE_LIQUIDITY"


@dataclass
class SwingPoint:
    timestamp_ms: int
    price: float
    is_high: bool
    level_type: str = "MAJOR"  # MAJOR (External), MINOR (Internal), MICRO
    is_protected: bool = False
    is_weak: bool = False
    is_invalidated: bool = False
    bar_index: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralBreak:
    timestamp_ms: int
    break_type: StructuralBreakType
    trigger_price: float
    broken_swing_price: float
    is_internal: bool = False
    is_valid: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructureSnapshot:
    external_trend: TrendDirection = TrendDirection.NEUTRAL
    internal_trend: TrendDirection = TrendDirection.NEUTRAL
    last_major_high: Optional[SwingPoint] = None
    last_major_low: Optional[SwingPoint] = None
    last_minor_high: Optional[SwingPoint] = None
    last_minor_low: Optional[SwingPoint] = None
    recent_breaks: List[StructuralBreak] = field(default_factory=list)
    protected_high: Optional[float] = None
    protected_low: Optional[float] = None
    weak_high: Optional[float] = None
    weak_low: Optional[float] = None
    trend_strength: float = 0.0


@dataclass
class KeyZone:
    zone_id: str
    zone_type: str  # ORDER_BLOCK, FVG, IMBALANCE, SUPPLY_DEMAND, LIQUIDITY, SUPPORT_RESISTANCE
    high_price: float
    low_price: float
    created_at_ms: int
    is_bullish: bool
    is_external: bool = True  # External vs Internal zone
    is_mitigated: bool = False
    mitigated_at_ms: Optional[int] = None
    strength: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LiquidityPool:
    pool_id: str
    liquidity_type: LiquidityType
    price_level: float
    timestamp_ms: int
    is_swept: bool = False
    swept_at_ms: Optional[int] = None


@dataclass
class ZonesSnapshot:
    order_blocks: List[KeyZone] = field(default_factory=list)
    fair_value_gaps: List[KeyZone] = field(default_factory=list)
    liquidity_pools: List[LiquidityPool] = field(default_factory=list)
    support_resistance: List[KeyZone] = field(default_factory=list)
    supply_demand: List[KeyZone] = field(default_factory=list)
    premium_discount_zone: str = "EQUILIBRIUM"  # PREMIUM, DISCOUNT, EQUILIBRIUM
    equilibrium_price: Optional[float] = None
    fibonacci_levels: Dict[str, float] = field(default_factory=dict)
    previous_high: Optional[float] = None
    previous_low: Optional[float] = None


@dataclass
class PhaseSnapshot:
    external_phase: MarketPhaseType = MarketPhaseType.UNCERTAIN
    internal_phase: MarketPhaseType = MarketPhaseType.UNCERTAIN
    current_phase: MarketPhaseType = MarketPhaseType.UNCERTAIN  # Primary shorthand
    depth_pct: float = 0.0
    duration_bars: int = 0
    is_compressed: bool = False
    is_displaced: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeasurementsSnapshot:
    atr: float = 0.0
    atr_bps: float = 0.0
    realized_vol: float = 0.0
    volume_sma_ratio: float = 1.0
    rsi: float = 50.0
    adx: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketState:
    symbol: str
    timestamp_ms: int
    timeframe: str
    close_price: float
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    volume: float = 0.0
    structure: StructureSnapshot = field(default_factory=StructureSnapshot)
    zones: ZonesSnapshot = field(default_factory=ZonesSnapshot)
    phase: PhaseSnapshot = field(default_factory=PhaseSnapshot)
    measurements: MeasurementsSnapshot = field(default_factory=MeasurementsSnapshot)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable dictionary representation."""
        def _serialize(obj):
            if hasattr(obj, "__dict__"):
                res = {}
                for k, v in obj.__dict__.items():
                    if isinstance(v, Enum):
                        res[k] = v.value
                    elif isinstance(v, list):
                        res[k] = [_serialize(i) for i in v]
                    elif hasattr(v, "__dict__"):
                        res[k] = _serialize(v)
                    else:
                        res[k] = v
                return res
            return obj
        return _serialize(self)
