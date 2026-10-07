"""Psychological & Round Number Levels Engine.

Identifies key round-number psychological price levels (e.g., $100, $1,000, $10,000, $50,000, $100,000)
acting as natural institutional cluster zones.
"""
from __future__ import annotations

import math
from typing import List
from market_model.contracts import KeyZone


class PsychologicalLevelsEngine:
    """Causal identifier for psychological round numbers."""

    def __init__(self, step_percentage: float = 0.05):
        self.step_percentage = step_percentage

    def detect_levels(self, current_price: float, count: int = 5) -> List[KeyZone]:
        """Generate nearest round psychological levels above and below current price."""
        if current_price <= 0:
            return []

        # Determine round order of magnitude
        magnitude = 10 ** math.floor(math.log10(current_price))
        step = magnitude / 2.0 if current_price / magnitude > 5 else magnitude / 5.0
        if step == 0:
            step = 1.0

        base = math.floor(current_price / step) * step
        levels: List[KeyZone] = []

        for i in range(-count, count + 1):
            px = base + i * step
            if px <= 0:
                continue
            is_above = px > current_price
            levels.append(
                KeyZone(
                    zone_id=f"PSYCH_{int(px)}",
                    zone_type="PSYCHOLOGICAL",
                    high_price=px * 1.0005,
                    low_price=px * 0.9995,
                    created_at_ms=0,
                    is_bullish=not is_above,
                    is_external=False,
                    strength=1.0,
                )
            )

        return levels
