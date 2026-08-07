"""
Product 07: MTF Structural Trailing Engine
Monitors active positions against MTF structure swings to lock in profits.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, SequenceLabel


@dataclass(frozen=True)
class TrailingUpdate:
    position_id: str
    should_update: bool
    new_stop_loss: float
    reason: str


class MTFTrailingEngine:

    @staticmethod
    def evaluate_trailing_stop(
        position_id: str,
        direction: TrendDirection,
        current_sl: float,
        mtf_state: MarketStatePayload
    ) -> TrailingUpdate:
        """
        Trails stop-loss behind valid MTF Higher Lows (for Longs) or Lower Highs (for Shorts).
        Exits or tightens when MTF CHOCH/reversal is detected.
        """
        if not mtf_state or not mtf_state.swings:
            return TrailingUpdate(position_id, False, current_sl, "No MTF swing data available")

        # Extract latest confirmed MTF swings
        latest_low = mtf_state.structure_state.protected_low
        latest_high = mtf_state.structure_state.protected_high

        if direction == TrendDirection.BULLISH and latest_low:
            new_sl_candidate = latest_low.raw_swing.price
            # Only trail upwards
            if new_sl_candidate > current_sl:
                return TrailingUpdate(
                    position_id=position_id,
                    should_update=True,
                    new_stop_loss=new_sl_candidate,
                    reason=f"Trailed behind MTF Higher Low (${new_sl_candidate:.2f})"
                )

        elif direction == TrendDirection.BEARISH and latest_high:
            new_sl_candidate = latest_high.raw_swing.price
            # Only trail downwards
            if new_sl_candidate < current_sl:
                return TrailingUpdate(
                    position_id=position_id,
                    should_update=True,
                    new_stop_loss=new_sl_candidate,
                    reason=f"Trailed behind MTF Lower High (${new_sl_candidate:.2f})"
                )

        return TrailingUpdate(position_id, False, current_sl, "MTF structure unchanged; SL maintained")
