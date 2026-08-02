"""
Product 01: Crypto Platform - HTF Bias & Target Engine
Implements Part C & Part F of strategy_specification.md v1.1 with Trend Persistence.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, EventType, MarketPhase


@dataclass
class HTFBiasResult:
    bias: TrendDirection
    expected_phase: MarketPhase
    target_tp_price: Optional[float]
    is_valid: bool
    rejection_reason: str = ""


class HTFBiasEngine:

    @staticmethod
    def evaluate_bias(htf_state: MarketStatePayload) -> HTFBiasResult:
        """Determines macro directional bias and structural TP target from HTF state."""
        if htf_state.trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return HTFBiasResult(
                bias=TrendDirection.NEUTRAL,
                expected_phase=MarketPhase.RANGE,
                target_tp_price=None,
                is_valid=False,
                rejection_reason=f"HTF trend is {htf_state.trend.value} (Requires BULLISH or BEARISH BOS/CHOCH close)."
            )

        # Rule: Last HTF event must align with current trend direction to confirm persistence
        if htf_state.last_event and htf_state.last_event.direction != htf_state.trend:
            return HTFBiasResult(
                bias=htf_state.trend,
                expected_phase=MarketPhase.RANGE,
                target_tp_price=None,
                is_valid=False,
                rejection_reason=f"HTF event ({htf_state.last_event.direction.value}) opposes active HTF trend ({htf_state.trend.value})."
            )

        # Bullish Bias Assessment
        if htf_state.trend == TrendDirection.BULLISH:
            tp_target = htf_state.protected_high
            
            # Structural Fallback: Use highest active swing high if protected_high is None
            if tp_target is None and htf_state.active_swings:
                high_swings = [s.price for s in htf_state.active_swings if s.swing_type.value == "HIGH"]
                if high_swings:
                    tp_target = max(high_swings)

            if tp_target is None:
                return HTFBiasResult(
                    bias=TrendDirection.BULLISH,
                    expected_phase=MarketPhase.CONTINUATION,
                    target_tp_price=None,
                    is_valid=False,
                    rejection_reason="HTF trend is BULLISH but target TP price is None."
                )

            expected_phase = MarketPhase.PULLBACK if (htf_state.last_event and htf_state.last_event.event_type == EventType.BOS) else MarketPhase.CONTINUATION

            return HTFBiasResult(
                bias=TrendDirection.BULLISH,
                expected_phase=expected_phase,
                target_tp_price=tp_target,
                is_valid=True,
                rejection_reason=""
            )

        # Bearish Bias Assessment
        elif htf_state.trend == TrendDirection.BEARISH:
            tp_target = htf_state.protected_low
            
            # Structural Fallback: Use lowest active swing low if protected_low is None
            if tp_target is None and htf_state.active_swings:
                low_swings = [s.price for s in htf_state.active_swings if s.swing_type.value == "LOW"]
                if low_swings:
                    tp_target = min(low_swings)

            if tp_target is None:
                return HTFBiasResult(
                    bias=TrendDirection.BEARISH,
                    expected_phase=MarketPhase.CONTINUATION,
                    target_tp_price=None,
                    is_valid=False,
                    rejection_reason="HTF trend is BEARISH but target TP price is None."
                )

            expected_phase = MarketPhase.PULLBACK if (htf_state.last_event and htf_state.last_event.event_type == EventType.BOS) else MarketPhase.CONTINUATION

            return HTFBiasResult(
                bias=TrendDirection.BEARISH,
                expected_phase=expected_phase,
                target_tp_price=tp_target,
                is_valid=True,
                rejection_reason=""
            )

        return HTFBiasResult(
            bias=TrendDirection.NEUTRAL,
            expected_phase=MarketPhase.RANGE,
            target_tp_price=None,
            is_valid=False,
            rejection_reason="Undefined HTF state."
        )