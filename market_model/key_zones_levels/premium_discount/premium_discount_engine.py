"""Premium, Discount & Equilibrium Engine.

Calculates dealing range bounds, equilibrium (50%), premium/discount zone state,
and Fibonacci retracement levels.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np

from market_model.contracts import StructureSnapshot


class PremiumDiscountEngine:
    """Causal engine for evaluating Dealing Range Equilibrium and Premium/Discount state."""

    def __init__(self, equilibrium_buffer_pct: float = 0.05):
        self.equilibrium_buffer_pct = equilibrium_buffer_pct

    def compute_dealing_range(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        structure: StructureSnapshot,
    ) -> Tuple[float, float, float, str, Dict[str, float]]:
        """Calculate range_high, range_low, equilibrium_price, pd_zone, and fibonacci_levels."""
        if structure.last_major_high and structure.last_major_low:
            range_h = max(structure.last_major_high.price, structure.last_major_low.price)
            range_l = min(structure.last_major_high.price, structure.last_major_low.price)
        else:
            range_h = float(np.max(highs[-50:])) if len(highs) >= 50 else float(np.max(highs))
            range_l = float(np.min(lows[-50:])) if len(lows) >= 50 else float(np.min(lows))

        eq_price = (range_h + range_l) / 2.0
        range_span = max(range_h - range_l, 1e-6)
        curr_close = closes[-1] if len(closes) > 0 else eq_price

        buf = self.equilibrium_buffer_pct * range_span
        if curr_close > eq_price + buf:
            pd_zone = "PREMIUM"
        elif curr_close < eq_price - buf:
            pd_zone = "DISCOUNT"
        else:
            pd_zone = "EQUILIBRIUM"

        fibs = {
            "fib_0_000": range_l,
            "fib_0_236": range_l + 0.236 * range_span,
            "fib_0_382": range_l + 0.382 * range_span,
            "fib_0_500": eq_price,
            "fib_0_618": range_l + 0.618 * range_span,
            "fib_0_705": range_l + 0.705 * range_span,  # OTE
            "fib_0_786": range_l + 0.786 * range_span,
            "fib_1_000": range_h,
        }

        return range_h, range_l, eq_price, pd_zone, fibs
