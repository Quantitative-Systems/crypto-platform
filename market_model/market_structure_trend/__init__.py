"""Market Structure & Trend Package.

Exposes causal structure detection engines:
- Swing point detection (Major & Minor)
- Break of Structure (BOS), Change of Character (CHoCH), Market Structure Shift (MSS)
- Internal vs External structure tracking
- Protected vs Weak swing identification
"""
from market_model.market_structure_trend.trend.structure_engine import StructureEngine

__all__ = ["StructureEngine"]
