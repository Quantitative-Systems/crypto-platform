"""Phase A Strategy Discovery Families (10 Canonical Families).

Each family is formulated using the 3 frozen Market Model dimensions:
1. STRUCTURE & TREND
2. KEY ZONES & LEVELS
3. PHASE

Available Families:
- F01_STRUCTURE_PHASE: Pure Structure + Phase
- F02_STRUCTURE_ZONE_PHASE: Structure + Key Zone + Phase
- F03_STRUCTURE_EMA_PHASE: Structure + EMA + Phase
- F04_STRUCTURE_LIQUIDITY_PHASE: Structure + Liquidity + Phase
- F05_STRUCTURE_OB_PHASE: Structure + Order Block + Phase
- F06_STRUCTURE_FVG_PHASE: Structure + Fair Value Gap + Phase
- F07_STRUCTURE_SUPPLY_DEMAND_PHASE: Structure + Supply/Demand + Phase
- F08_STRUCTURE_TRENDLINE_PHASE: Structure + Trendline + Phase
- F09_STRUCTURE_FIBONACCI_PHASE: Structure + Fibonacci + Phase
- F10_STRUCTURE_MOMENTUM_PHASE: Structure + Momentum + Phase
"""
from typing import Dict, Type
from strategy.families.base_family import BaseStrategyFamily
from strategy.families.f01_structure_phase import StructurePhaseFamily
from strategy.families.f02_structure_zone_phase import StructureZonePhaseFamily
from strategy.families.f03_structure_ema_phase import StructureEMAPhaseFamily
from strategy.families.f04_structure_liquidity_phase import StructureLiquidityPhaseFamily
from strategy.families.f05_structure_ob_phase import StructureOBPhaseFamily
from strategy.families.f06_structure_fvg_phase import StructureFVGPhaseFamily
from strategy.families.f07_structure_sd_phase import StructureSupplyDemandPhaseFamily
from strategy.families.f08_structure_trendline_phase import StructureTrendlinePhaseFamily
from strategy.families.f09_structure_fibonacci_phase import StructureFibonacciPhaseFamily
from strategy.families.f10_structure_momentum_phase import StructureMomentumPhaseFamily

FAMILY_REGISTRY: Dict[str, Type[BaseStrategyFamily]] = {
    "F01_STRUCTURE_PHASE": StructurePhaseFamily,
    "F02_STRUCTURE_ZONE_PHASE": StructureZonePhaseFamily,
    "F03_STRUCTURE_EMA_PHASE": StructureEMAPhaseFamily,
    "F04_STRUCTURE_LIQUIDITY_PHASE": StructureLiquidityPhaseFamily,
    "F05_STRUCTURE_OB_PHASE": StructureOBPhaseFamily,
    "F06_STRUCTURE_FVG_PHASE": StructureFVGPhaseFamily,
    "F07_STRUCTURE_SUPPLY_DEMAND_PHASE": StructureSupplyDemandPhaseFamily,
    "F08_STRUCTURE_TRENDLINE_PHASE": StructureTrendlinePhaseFamily,
    "F09_STRUCTURE_FIBONACCI_PHASE": StructureFibonacciPhaseFamily,
    "F10_STRUCTURE_MOMENTUM_PHASE": StructureMomentumPhaseFamily,
}

__all__ = [
    "BaseStrategyFamily",
    "StructurePhaseFamily",
    "StructureZonePhaseFamily",
    "StructureEMAPhaseFamily",
    "StructureLiquidityPhaseFamily",
    "StructureOBPhaseFamily",
    "StructureFVGPhaseFamily",
    "StructureSupplyDemandPhaseFamily",
    "StructureTrendlinePhaseFamily",
    "StructureFibonacciPhaseFamily",
    "StructureMomentumPhaseFamily",
    "FAMILY_REGISTRY",
]


