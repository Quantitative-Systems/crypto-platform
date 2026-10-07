"""Family 09: Structure + Fibonacci (OTE) + Phase (Repaired).

Requires genuine causal price pullback into the Optimal Trade Entry (OTE) Fibonacci zone:
- Retracement bounded between 50.0% and 78.6% levels.
- Rejects if Fibonacci levels are absent.
"""
from __future__ import annotations

from market_model.contracts import MarketState
from strategy.families.base_family import BaseStrategyFamily


class StructureFibonacciPhaseFamily(BaseStrategyFamily):
    """Family 09: Structure + Fibonacci + Phase."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        phase_mode: str = "PULLBACK",
        min_target_r: float = 4.0,
    ):
        super().__init__(
            family_id="F09_STRUCTURE_FIBONACCI_PHASE",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
        )

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Genuine causal Fibonacci OTE check."""
        fibs = mtf_state.zones.fibonacci_levels
        if not fibs or "fib_0_500" not in fibs or "fib_0_618" not in fibs:
            return False

        curr_px = mtf_state.close_price
        fib_50 = fibs["fib_0_500"]
        fib_786 = fibs.get("fib_0_786", fibs.get("fib_0_618"))

        lower = min(fib_50, fib_786)
        upper = max(fib_50, fib_786)

        if direction == 1:
            return lower * 0.995 <= curr_px <= upper * 1.005
        elif direction == -1:
            return lower * 0.995 <= curr_px <= upper * 1.005

        return False
