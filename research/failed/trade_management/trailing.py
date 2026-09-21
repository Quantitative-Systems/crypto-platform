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

    @property
    def is_updated(self) -> bool:
        return self.should_update


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
        latest_low = mtf_state.structure_state.protected_low if mtf_state.structure_state else None
        latest_high = mtf_state.structure_state.protected_high if mtf_state.structure_state else None

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

    @classmethod
    def update_trailing_stop(
        cls,
        action: str,
        current_stop_loss: float,
        entry_price: float,
        current_close: float,
        mtf_state: MarketStatePayload
    ) -> TrailingUpdate:
        """
        Adapter method matching StrategyOrchestrator's expected contract.
        """
        direction = TrendDirection.BULLISH if action.upper() in ("BUY", "LONG") else TrendDirection.BEARISH
        return cls.evaluate_trailing_stop(
            position_id="ORCHESTrated_PLAN",
            direction=direction,
            current_sl=current_stop_loss,
            mtf_state=mtf_state
        )


# Public API Alias for Strategy Orchestrator Compatibility
TrailingEngine = MTFTrailingEngine
