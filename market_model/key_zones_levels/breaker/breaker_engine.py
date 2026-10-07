"""Breaker Block Engine.

A Breaker Block is a validated Order Block that failed (was impulsively violated),
flipping its polarity (bullish order block becomes bearish resistance breaker, and vice versa).
"""
from __future__ import annotations

from typing import List
import numpy as np

from market_model.contracts import KeyZone


class BreakerBlockEngine:
    """Causal identifier for Breaker Blocks flipping order block polarity."""

    def detect_breaker_blocks(
        self,
        order_blocks: List[KeyZone],
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        timestamps: np.ndarray,
    ) -> List[KeyZone]:
        """Detect order blocks that have been breached and now act as flipped polarity zones."""
        breakers: List[KeyZone] = []
        if len(closes) == 0:
            return breakers

        curr_close = closes[-1]

        for ob in order_blocks:
            if not ob.is_mitigated:
                continue

            # If bullish order block had price close below its low, it flips into a Bearish Breaker
            if ob.is_bullish and curr_close < ob.low_price:
                breakers.append(
                    KeyZone(
                        zone_id=f"BREAKER_BEAR_{ob.zone_id}",
                        zone_type="BREAKER_BLOCK",
                        high_price=ob.high_price,
                        low_price=ob.low_price,
                        created_at_ms=int(timestamps[-1]),
                        is_bullish=False,
                        is_external=ob.is_external,
                        strength=ob.strength * 1.2,
                    )
                )
            # If bearish order block had price close above its high, it flips into a Bullish Breaker
            elif not ob.is_bullish and curr_close > ob.high_price:
                breakers.append(
                    KeyZone(
                        zone_id=f"BREAKER_BULL_{ob.zone_id}",
                        zone_type="BREAKER_BLOCK",
                        high_price=ob.high_price,
                        low_price=ob.low_price,
                        created_at_ms=int(timestamps[-1]),
                        is_bullish=True,
                        is_external=ob.is_external,
                        strength=ob.strength * 1.2,
                    )
                )

        return breakers
