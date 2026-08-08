"""
Product 01: Crypto Platform - HTF Bias & Destination Engine (V2.1)
Parses HTF MarketStatePayload to extract macro bias, target TP objective, and market phase.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, MarketPhase


@dataclass
class HTFBiasResult:
    bias: TrendDirection
    target_tp_price: Optional[float]
    expected_phase: MarketPhase
    is_valid: bool
    rejection_reason: str = ""


class HTFBiasEngine:

    @staticmethod
    def evaluate_bias(htf_state: MarketStatePayload) -> HTFBiasResult:
        """Determines macro bias and target price from HTF MarketStatePayload."""
        trend = htf_state.structure_state.external_trend or htf_state.trend_state.direction or htf_state.trend

        if trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            if htf_state.current_candle.is_bullish:
                trend = TrendDirection.BULLISH
            elif htf_state.current_candle.is_bearish:
                trend = TrendDirection.BEARISH

        if trend == TrendDirection.NEUTRAL:
            return HTFBiasResult(
                bias=TrendDirection.NEUTRAL,
                target_tp_price=None,
                expected_phase=htf_state.phase_state.current_phase,
                is_valid=False,
                rejection_reason="HTF trend is completely Neutral."
            )

        target_tp = None
        if trend == TrendDirection.BULLISH:
            if htf_state.structure_state.protected_high:
                target_tp = htf_state.structure_state.protected_high.raw_swing.price
            else:
                target_tp = htf_state.current_price * 1.05
        elif trend == TrendDirection.BEARISH:
            if htf_state.structure_state.protected_low:
                target_tp = htf_state.structure_state.protected_low.raw_swing.price
            else:
                target_tp = htf_state.current_price * 0.95

        expected_phase = htf_state.phase_state.current_phase
        if expected_phase in (MarketPhase.EXPANSION, MarketPhase.AWAITING_CONFIRMATION):
            expected_phase = MarketPhase.PULLBACK if trend == TrendDirection.BULLISH else MarketPhase.CONTINUATION

        return HTFBiasResult(
            bias=trend,
            target_tp_price=target_tp,
            expected_phase=expected_phase,
            is_valid=True,
            rejection_reason=""
        )