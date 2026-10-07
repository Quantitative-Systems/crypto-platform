"""Order Blocks Engine.

Identifies structural Order Blocks associated with displacement and structure breaks.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from market_model.contracts import KeyZone, StructureSnapshot


class OrderBlockEngine:
    """Causal engine for detecting and tracking Order Blocks."""

    def __init__(self, max_active_zones: int = 20):
        self.max_active_zones = max_active_zones

    def detect_order_blocks(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        structure: StructureSnapshot,
    ) -> List[KeyZone]:
        """Detect Order Blocks associated with displacement / structure breaks."""
        n = len(closes)
        obs: List[KeyZone] = []
        if n < 5:
            return obs

        scan_start = max(1, n - 150)
        for i in range(scan_start, n - 1):
            body_i = abs(closes[i] - opens[i])
            disp_next = closes[i + 1] - opens[i + 1]

            # Bullish OB: down candle followed by strong bullish displacement
            if closes[i] < opens[i] and disp_next > body_i * 1.5 and closes[i + 1] > highs[i]:
                is_mit = any(lows[k] <= lows[i] for k in range(i + 2, n))
                obs.append(
                    KeyZone(
                        zone_id=f"OB_BULL_{timestamps[i]}",
                        zone_type="ORDER_BLOCK",
                        high_price=float(highs[i]),
                        low_price=float(lows[i]),
                        created_at_ms=int(timestamps[i]),
                        is_bullish=True,
                        is_external=True,
                        is_mitigated=is_mit,
                        strength=2.0,
                    )
                )

            # Bearish OB: up candle followed by strong bearish displacement
            elif closes[i] > opens[i] and -disp_next > body_i * 1.5 and closes[i + 1] < lows[i]:
                is_mit = any(highs[k] >= highs[i] for k in range(i + 2, n))
                obs.append(
                    KeyZone(
                        zone_id=f"OB_BEAR_{timestamps[i]}",
                        zone_type="ORDER_BLOCK",
                        high_price=float(highs[i]),
                        low_price=float(lows[i]),
                        created_at_ms=int(timestamps[i]),
                        is_bullish=False,
                        is_external=True,
                        is_mitigated=is_mit,
                        strength=2.0,
                    )
                )

        return obs[-self.max_active_zones :]
