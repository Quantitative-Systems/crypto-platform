"""
Product 01: Crypto Platform - Dynamic MTF Trailing Stop Manager
Implements Part H of strategy_specification.md v1.1.
"""

from dataclasses import dataclass
from market_intelligence.primitives import MarketStatePayload


@dataclass
class TrailingUpdateResult:
    new_stop_loss: float
    is_updated: bool
    reason: str


class TrailingEngine:

    @staticmethod
    def update_trailing_stop(
        action: str,  # "BUY" or "SELL"
        current_stop_loss: float,
        mtf_state: MarketStatePayload
    ) -> TrailingUpdateResult:
        """Trails Stop Loss behind MTF protected structural swings."""
        
        # Long Position Trailing
        if action == "BUY":
            if mtf_state.protected_low and mtf_state.protected_low > current_stop_loss:
                return TrailingUpdateResult(
                    new_stop_loss=mtf_state.protected_low,
                    is_updated=True,
                    reason=f"Trailed SL up to new MTF protected low: ${mtf_state.protected_low:.2f}"
                )

        # Short Position Trailing
        elif action == "SELL":
            if mtf_state.protected_high and mtf_state.protected_high < current_stop_loss:
                return TrailingUpdateResult(
                    new_stop_loss=mtf_state.protected_high,
                    is_updated=True,
                    reason=f"Trailed SL down to new MTF protected high: ${mtf_state.protected_high:.2f}"
                )

        return TrailingUpdateResult(
            new_stop_loss=current_stop_loss,
            is_updated=False,
            reason="Stop loss remains unchanged."
        )