"""Swing Levels Engine.

Identifies major and minor swing highs and lows, tracking structural pivot levels.
"""
from __future__ import annotations

from typing import List
import numpy as np

from market_model.contracts import KeyZone, StructureSnapshot


class SwingLevelsEngine:
    """Causal identifier for key horizontal levels derived from swing pivots."""

    def derive_swing_zones(self, structure: StructureSnapshot) -> List[KeyZone]:
        """Convert confirmed swing points into horizontal reference KeyZones."""
        zones: List[KeyZone] = []
        if structure.last_major_high:
            px = structure.last_major_high.price
            zones.append(
                KeyZone(
                    zone_id=f"SWING_HIGH_{structure.last_major_high.timestamp_ms}",
                    zone_type="SWING_LEVEL",
                    high_price=px * 1.0005,
                    low_price=px * 0.9995,
                    created_at_ms=structure.last_major_high.timestamp_ms,
                    is_bullish=False,
                    is_external=True,
                )
            )
        if structure.last_major_low:
            px = structure.last_major_low.price
            zones.append(
                KeyZone(
                    zone_id=f"SWING_LOW_{structure.last_major_low.timestamp_ms}",
                    zone_type="SWING_LEVEL",
                    high_price=px * 1.0005,
                    low_price=px * 0.9995,
                    created_at_ms=structure.last_major_low.timestamp_ms,
                    is_bullish=True,
                    is_external=True,
                )
            )
        return zones
