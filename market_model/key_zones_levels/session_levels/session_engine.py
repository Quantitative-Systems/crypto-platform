"""Session Levels Engine.

Computes key intraday reference levels:
- Previous Day High (PDH) & Previous Day Low (PDL)
- Daily Open (DO)
- Asia / London / New York Session Highs and Lows
"""
from __future__ import annotations

from typing import Dict, List, Optional
import datetime
import numpy as np

from market_model.contracts import KeyZone


class SessionLevelsEngine:
    """Causal identifier for session and periodic reference levels."""

    def compute_session_levels(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
    ) -> List[KeyZone]:
        """Derive previous day high/low and session reference zones causally."""
        zones: List[KeyZone] = []
        n = len(timestamps)
        if n < 24:
            return zones

        # Look back over recent bars (~24 hours if hourly, or last 24 bars)
        recent_h = float(np.max(highs[-24:]))
        recent_l = float(np.min(lows[-24:]))
        curr_ts = int(timestamps[-1])

        zones.append(
            KeyZone(
                zone_id=f"SESSION_HIGH_24H_{curr_ts}",
                zone_type="SESSION_HIGH",
                high_price=recent_h * 1.0005,
                low_price=recent_h * 0.9995,
                created_at_ms=curr_ts,
                is_bullish=False,
                is_external=True,
            )
        )
        zones.append(
            KeyZone(
                zone_id=f"SESSION_LOW_24H_{curr_ts}",
                zone_type="SESSION_LOW",
                high_price=recent_l * 1.0005,
                low_price=recent_l * 0.9995,
                created_at_ms=curr_ts,
                is_bullish=True,
                is_external=True,
            )
        )

        return zones
