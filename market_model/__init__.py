"""Canonical Market Model Package.

Exposes the 3 strategy-agnostic core dimensions:
1. STRUCTURE & TREND (StructureEngine)
2. KEY ZONES & LEVELS (KeyZonesEngine)
3. PHASE (PhaseEngine)

And the MarketState contract & MarketStateGenerator for generating pure descriptive snapshots across timeframes.
"""
from market_model.contracts import (
    MarketState,
    StructureSnapshot,
    ZonesSnapshot,
    PhaseSnapshot,
    MeasurementsSnapshot,
    SwingPoint,
    StructuralBreak,
    StructuralBreakType,
    TrendDirection,
    KeyZone,
    LiquidityPool,
    LiquidityType,
    MarketPhaseType,
)
from market_model.market_structure_trend.trend.structure_engine import StructureEngine
from market_model.key_zones_levels.order_blocks.key_zones_engine import KeyZonesEngine
from market_model.phases.pullback.detection.phase_engine import PhaseEngine
from market_model.state_generator import MarketStateGenerator

__all__ = [
    "MarketStateGenerator",
    "StructureEngine",
    "KeyZonesEngine",
    "PhaseEngine",
    "MarketState",
    "StructureSnapshot",
    "ZonesSnapshot",
    "PhaseSnapshot",
    "MeasurementsSnapshot",
    "SwingPoint",
    "StructuralBreak",
    "StructuralBreakType",
    "TrendDirection",
    "KeyZone",
    "LiquidityPool",
    "LiquidityType",
    "MarketPhaseType",
]
