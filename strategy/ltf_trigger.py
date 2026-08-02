"""
Product 01: Crypto Platform - LTF Entry Trigger Engine
Implements Part E of strategy_specification.md v1.1.
"""

from dataclasses import dataclass
from market_intelligence.primitives import MarketStatePayload, TrendDirection, Candle
from strategy.mtf_setup import MTFSetupResult


@dataclass
class LTFTriggerResult:
    is_triggered: bool
    entry_price: float
    stop_loss_price: float
    trigger_reason: str = ""


class LTFTriggerEngine:

    @staticmethod
    def evaluate_entry(
        ltf_state: MarketStatePayload,
        latest_candle: Candle,
        mtf_setup: MTFSetupResult,
        htf_bias: TrendDirection
    ) -> LTFTriggerResult:
        """Verifies LTF KeyZone interaction, Liquidity Sweep & Invalidation SL at Keyzone boundary."""
        if not mtf_setup.is_aligned or not mtf_setup.active_mtf_keyzone:
            return LTFTriggerResult(
                is_triggered=False, entry_price=0.0, stop_loss_price=0.0,
                trigger_reason="MTF setup is not aligned."
            )

        keyzone = mtf_setup.active_mtf_keyzone

        # Bullish Trigger Check
        if htf_bias == TrendDirection.BULLISH:
            # Rule 1: Candle low penetrates keyzone range
            if latest_candle.low <= keyzone.high:
                entry_price = latest_candle.close
                # Rule 2: Invalidation SL placed strictly at structural KeyZone low boundary
                stop_loss = keyzone.low

                if entry_price > stop_loss:
                    return LTFTriggerResult(
                        is_triggered=True,
                        entry_price=entry_price,
                        stop_loss_price=stop_loss,
                        trigger_reason="Bullish KeyZone mitigation & LTF displacement close."
                    )

        # Bearish Trigger Check
        elif htf_bias == TrendDirection.BEARISH:
            if latest_candle.high >= keyzone.low:
                entry_price = latest_candle.close
                # Invalidation SL placed strictly at structural KeyZone high boundary
                stop_loss = keyzone.high

                if entry_price < stop_loss:
                    return LTFTriggerResult(
                        is_triggered=True,
                        entry_price=entry_price,
                        stop_loss_price=stop_loss,
                        trigger_reason="Bearish KeyZone mitigation & LTF displacement close."
                    )

        return LTFTriggerResult(
            is_triggered=False, entry_price=0.0, stop_loss_price=0.0,
            trigger_reason="No LTF keyzone interaction detected."
        )