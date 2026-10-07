"""Fair Value Gaps (FVG) / Imbalance Engine.

Identifies 3-bar Fair Value Gaps and tracks their mitigation status causally.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from market_model.contracts import KeyZone


class FVGEngine:
    """Causal engine for detecting and tracking Fair Value Gaps."""

    def __init__(self, fvg_min_bps: float = 5.0, max_active_zones: int = 20):
        self.fvg_min_bps = fvg_min_bps
        self.max_active_zones = max_active_zones

    def detect_fair_value_gaps(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, timestamps: np.ndarray
    ) -> List[KeyZone]:
        """Detect Fair Value Gaps (FVG / Imbalances) and track mitigation."""
        n = len(closes)
        fvgs: List[KeyZone] = []
        if n < 3:
            return fvgs

        scan_start = max(2, n - 200)
        for i in range(scan_start, n):
            # Bullish FVG: Low of bar i > High of bar i-2
            if lows[i] > highs[i - 2]:
                gap_size_bps = (lows[i] - highs[i - 2]) / highs[i - 2] * 1e4
                if gap_size_bps >= self.fvg_min_bps:
                    z_high = float(lows[i])
                    z_low = float(highs[i - 2])
                    is_mit = False
                    mit_ts = None
                    for k in range(i + 1, n):
                        if lows[k] <= z_high:
                            is_mit = True
                            mit_ts = int(timestamps[k])
                            break
                    fvgs.append(
                        KeyZone(
                            zone_id=f"FVG_BULL_{timestamps[i-1]}",
                            zone_type="FAIR_VALUE_GAP",
                            high_price=z_high,
                            low_price=z_low,
                            created_at_ms=int(timestamps[i]),
                            is_bullish=True,
                            is_external=True,
                            is_mitigated=is_mit,
                            mitigated_at_ms=mit_ts,
                            strength=float(gap_size_bps),
                        )
                    )

            # Bearish FVG: High of bar i < Low of bar i-2
            elif highs[i] < lows[i - 2]:
                gap_size_bps = (lows[i - 2] - highs[i]) / lows[i - 2] * 1e4
                if gap_size_bps >= self.fvg_min_bps:
                    z_high = float(lows[i - 2])
                    z_low = float(highs[i])
                    is_mit = False
                    mit_ts = None
                    for k in range(i + 1, n):
                        if highs[k] >= z_low:
                            is_mit = True
                            mit_ts = int(timestamps[k])
                            break
                    fvgs.append(
                        KeyZone(
                            zone_id=f"FVG_BEAR_{timestamps[i-1]}",
                            zone_type="FAIR_VALUE_GAP",
                            high_price=z_high,
                            low_price=z_low,
                            created_at_ms=int(timestamps[i]),
                            is_bullish=False,
                            is_external=True,
                            is_mitigated=is_mit,
                            mitigated_at_ms=mit_ts,
                            strength=float(gap_size_bps),
                        )
                    )

        return fvgs[-self.max_active_zones :]
