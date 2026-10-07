"""Fibonacci Retracement and Extension Engine.

Computes standard institutional Fibonacci retracements (38.2%, 50%, 61.8%, 70.5% OTE, 78.6%)
and extensions (127.2%, 161.8%) from major swing points.
"""
from __future__ import annotations

from typing import Dict, Optional
import numpy as np


class FibonacciEngine:
    """Causal Fibonacci level calculator based on structural swing swings."""

    FIB_RATIOS = {
        "fib_0_000": 0.0,
        "fib_0_236": 0.236,
        "fib_0_382": 0.382,
        "fib_0_500": 0.500,
        "fib_0_618": 0.618,
        "fib_0_705": 0.705,  # Optimal Trade Entry (OTE)
        "fib_0_786": 0.786,
        "fib_1_000": 1.000,
        "fib_1_272": 1.272,
        "fib_1_618": 1.618,
    }

    def compute_levels(
        self,
        swing_low: float,
        swing_high: float,
        is_bullish: bool = True,
    ) -> Dict[str, float]:
        """Compute price levels for Fibonacci ratios across a swing range."""
        span = swing_high - swing_low
        if span <= 0:
            return {k: swing_low for k in self.FIB_RATIOS}

        levels: Dict[str, float] = {}
        for name, ratio in self.FIB_RATIOS.items():
            if is_bullish:
                # Bullish retracement from high towards low
                levels[name] = swing_high - (ratio * span)
            else:
                # Bearish retracement from low towards high
                levels[name] = swing_low + (ratio * span)

        return levels
