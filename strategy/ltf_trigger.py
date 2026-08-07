"""
Product 01: Crypto Platform - LTF Entry Trigger Engine (V2.1)
Verifies LTF displacement candle closes off MTF KeyZones and calculates invalidation SL.
"""

from dataclasses import dataclass
from market_intelligence.primitives import MarketStatePayload, Candle, TrendDirection
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
        htf_bias: TrendDirection,
        buffer_pct: float = 0.0015
    ) -> LTFTriggerResult:
        """Verifies LTF KeyZone interaction + Displacement Close."""
        if not mtf_setup.is_aligned or not mtf_setup.active_mtf_keyzone:
            return LTFTriggerResult(
                is_triggered=False, entry_price=0.0, stop_loss_price=0.0,
                trigger_reason="MTF setup is not aligned."
            )

        keyzone = mtf_setup.active_mtf_keyzone

        # Bullish Trigger: Candle low interacts with keyzone AND closes GREEN
        if htf_bias == TrendDirection.BULLISH:
            if latest_candle.low <= keyzone.high and latest_candle.close > latest_candle.open:
                entry_price = latest_candle.close
                stop_loss = keyzone.low * (1.0 - buffer_pct)

                if entry_price > stop_loss:
                    return LTFTriggerResult(
                        is_triggered=True,
                        entry_price=entry_price,
                        stop_loss_price=stop_loss,
                        trigger_reason="Bullish KeyZone interaction + Bullish Displacement Close."
                    )

        # Bearish Trigger: Candle high interacts with keyzone AND closes RED
        elif htf_bias == TrendDirection.BEARISH:
            if latest_candle.high >= keyzone.low and latest_candle.close < latest_candle.open:
                entry_price = latest_candle.close
                stop_loss = keyzone.high * (1.0 + buffer_pct)

                if entry_price < stop_loss:
                    return LTFTriggerResult(
                        is_triggered=True,
                        entry_price=entry_price,
                        stop_loss_price=stop_loss,
                        trigger_reason="Bearish KeyZone interaction + Bearish Displacement Close."
                    )

        return LTFTriggerResult(
            is_triggered=False, entry_price=0.0, stop_loss_price=0.0,
            trigger_reason="No displacement confirmation close on KeyZone interaction."
        )