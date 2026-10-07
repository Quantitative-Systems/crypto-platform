"""Mitigation Tracking Engine.

Monitors active key zones (Order Blocks, FVGs, S/R) and determines whether subsequent
price action has causally tested, mitigated, or completely violated them.
"""
from __future__ import annotations

from typing import List, Tuple
import numpy as np

from market_model.contracts import KeyZone


class MitigationTracker:
    """Causal mitigation evaluator for KeyZones."""

    @staticmethod
    def update_mitigation(
        zones: List[KeyZone],
        current_high: float,
        current_low: float,
        current_timestamp_ms: int,
    ) -> List[KeyZone]:
        """Update mitigation status for zones given latest bar."""
        updated: List[KeyZone] = []
        for z in zones:
            if z.is_mitigated:
                updated.append(z)
                continue

            # Bullish zone mitigation: price dips into or below zone high
            if z.is_bullish and current_low <= z.high_price:
                updated.append(
                    KeyZone(
                        zone_id=z.zone_id,
                        zone_type=z.zone_type,
                        high_price=z.high_price,
                        low_price=z.low_price,
                        created_at_ms=z.created_at_ms,
                        is_bullish=z.is_bullish,
                        is_external=z.is_external,
                        is_mitigated=True,
                        mitigated_at_ms=current_timestamp_ms,
                        strength=z.strength,
                    )
                )
            # Bearish zone mitigation: price rises into or above zone low
            elif not z.is_bullish and current_high >= z.low_price:
                updated.append(
                    KeyZone(
                        zone_id=z.zone_id,
                        zone_type=z.zone_type,
                        high_price=z.high_price,
                        low_price=z.low_price,
                        created_at_ms=z.created_at_ms,
                        is_bullish=z.is_bullish,
                        is_external=z.is_external,
                        is_mitigated=True,
                        mitigated_at_ms=current_timestamp_ms,
                        strength=z.strength,
                    )
                )
            else:
                updated.append(z)

        return updated
