"""Supply & Demand Zones Engine.

Models supply zones (distribution origins before sharp drops) and demand zones
(accumulation origins before sharp rallies).
"""
from __future__ import annotations

from typing import List
import numpy as np

from market_model.contracts import KeyZone


class SupplyDemandEngine:
    """Causal identifier for institutional Supply and Demand zones."""

    def __init__(self, min_departure_mult: float = 2.0, max_active_zones: int = 15):
        self.min_departure_mult = min_departure_mult
        self.max_active_zones = max_active_zones

    def detect_zones(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
    ) -> List[KeyZone]:
        """Detect base candles preceding strong explosive departure moves."""
        zones: List[KeyZone] = []
        n = len(closes)
        if n < 5:
            return zones

        scan_start = max(1, n - 100)
        for i in range(scan_start, n - 1):
            base_body = abs(closes[i] - opens[i])
            if base_body == 0:
                base_body = closes[i] * 0.0001

            departure = abs(closes[i + 1] - opens[i + 1])
            if departure >= base_body * self.min_departure_mult:
                is_rally = closes[i + 1] > opens[i + 1]
                z_type = "DEMAND_ZONE" if is_rally else "SUPPLY_ZONE"
                zones.append(
                    KeyZone(
                        zone_id=f"{z_type}_{timestamps[i]}",
                        zone_type=z_type,
                        high_price=float(highs[i]),
                        low_price=float(lows[i]),
                        created_at_ms=int(timestamps[i]),
                        is_bullish=is_rally,
                        is_external=True,
                        strength=float(departure / base_body),
                    )
                )

        return zones[-self.max_active_zones :]
