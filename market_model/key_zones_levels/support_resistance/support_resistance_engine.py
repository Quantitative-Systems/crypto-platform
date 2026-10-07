"""Support & Resistance Levels Engine.

Identifies major horizontal support and resistance levels from structural swings,
previous high/low dealing ranges, and key structural pivots.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from market_model.contracts import KeyZone, StructureSnapshot


class SupportResistanceEngine:
    """Causal engine for detecting horizontal Support and Resistance zones."""

    def __init__(self, zone_buffer_bps: float = 10.0):
        self.zone_buffer_bps = zone_buffer_bps

    def detect_support_resistance(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        structure: StructureSnapshot,
    ) -> List[KeyZone]:
        """Derive Support and Resistance KeyZones from confirmed structural swing levels."""
        sr_zones: List[KeyZone] = []
        buf_frac = self.zone_buffer_bps / 1e4

        if structure.last_major_high:
            px = structure.last_major_high.price
            sr_zones.append(
                KeyZone(
                    zone_id=f"RESISTANCE_MAJOR_{structure.last_major_high.timestamp_ms}",
                    zone_type="RESISTANCE",
                    high_price=px * (1.0 + buf_frac),
                    low_price=px * (1.0 - buf_frac),
                    created_at_ms=structure.last_major_high.timestamp_ms,
                    is_bullish=False,
                    is_external=True,
                )
            )

        if structure.last_major_low:
            px = structure.last_major_low.price
            sr_zones.append(
                KeyZone(
                    zone_id=f"SUPPORT_MAJOR_{structure.last_major_low.timestamp_ms}",
                    zone_type="SUPPORT",
                    high_price=px * (1.0 + buf_frac),
                    low_price=px * (1.0 - buf_frac),
                    created_at_ms=structure.last_major_low.timestamp_ms,
                    is_bullish=True,
                    is_external=True,
                )
            )

        return sr_zones
