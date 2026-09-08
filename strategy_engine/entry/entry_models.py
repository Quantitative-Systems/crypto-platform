"""
Product 02 — Strategy Engine: Modular LTF Entry Models
Provides independently testable, directionally symmetric price-action entry models.
Enforces event recency within the active setup window and derives the immediate micro structural invalidation price.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, List
from market_intelligence.primitives import MarketStatePayload, Candle, StructureEvent


@dataclass(frozen=True)
class EntryEvaluationResult:
    is_confirmed: bool
    entry_model_name: str
    reversal_reason: str
    micro_invalidation_price: Optional[float]
    entry_price: Optional[float]

    def __bool__(self) -> bool:
        return self.is_confirmed


class BaseLTFEntryModel(ABC):
    @abstractmethod
    def evaluate(
        self,
        ltf_payload: MarketStatePayload,
        required_direction: str,  # "BULLISH" or "BEARISH"
        setup_retest_timestamp: int
    ) -> EntryEvaluationResult:
        pass


class DirectionalDisplacementModel(BaseLTFEntryModel):
    """
    Requires a decisive directional candle closing in the setup direction:
    - Long: Close > Open, body >= 50% of range, positive move >= min_expansion_pct.
    - Short: Close < Open, body >= 50% of range, negative move >= min_expansion_pct.
    """
    def __init__(self, min_body_ratio: float = 0.50, min_expansion_pct: float = 0.0008):
        self.min_body_ratio = min_body_ratio
        self.min_expansion_pct = min_expansion_pct

    def evaluate(
        self,
        ltf_payload: MarketStatePayload,
        required_direction: str,
        setup_retest_timestamp: int
    ) -> EntryEvaluationResult:
        c = ltf_payload.current_candle
        if not c:
            return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "NO_CANDLE", None, None)

        is_long = required_direction.upper() in ("BULLISH", "LONG", "BUY")
        total_range = c.high - c.low
        if total_range <= 0:
            return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "ZERO_RANGE", None, None)

        body = abs(c.close - c.open)
        body_ratio = body / total_range

        if body_ratio < self.min_body_ratio:
            return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "INSUFFICIENT_BODY_RATIO", None, None)

        if is_long:
            # Bullish close
            if c.close <= c.open:
                return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "BEARISH_CLOSE_IN_BULLISH_SETUP", None, None)
            expansion = (c.close - c.open) / c.open
            if expansion < self.min_expansion_pct:
                return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "INSUFFICIENT_EXPANSION", None, None)
            return EntryEvaluationResult(
                is_confirmed=True,
                entry_model_name="DIRECTIONAL_DISPLACEMENT",
                reversal_reason="BULLISH_DISPLACEMENT_CONFIRMED",
                micro_invalidation_price=c.low,
                entry_price=c.close
            )
        else:
            # Bearish close
            if c.close >= c.open:
                return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "BULLISH_CLOSE_IN_BEARISH_SETUP", None, None)
            expansion = (c.open - c.close) / c.open
            if expansion < self.min_expansion_pct:
                return EntryEvaluationResult(False, "DIRECTIONAL_DISPLACEMENT", "INSUFFICIENT_EXPANSION", None, None)
            return EntryEvaluationResult(
                is_confirmed=True,
                entry_model_name="DIRECTIONAL_DISPLACEMENT",
                reversal_reason="BEARISH_DISPLACEMENT_CONFIRMED",
                micro_invalidation_price=c.high,
                entry_price=c.close
            )


class LiquiditySweepAndDisplacementModel(BaseLTFEntryModel):
    """
    Canonical SMC Entry Model:
    Requires:
    1. A liquidity sweep in the setup direction occurring at or after the MTF retest timestamp.
    2. Directional displacement candle confirming reversal away from the swept level.
    """
    def __init__(self, max_event_age_bars: int = 12):
        self.max_event_age_bars = max_event_age_bars
        self.displacement_model = DirectionalDisplacementModel(min_body_ratio=0.45, min_expansion_pct=0.0005)

    def evaluate(
        self,
        ltf_payload: MarketStatePayload,
        required_direction: str,
        setup_retest_timestamp: int
    ) -> EntryEvaluationResult:
        is_long = required_direction.upper() in ("BULLISH", "LONG", "BUY")
        ltf_events = ltf_payload.events or []

        # 1. Check for causal liquidity sweep at or after setup retest timestamp
        sweep_events = []
        for ev in reversed(ltf_events):
            ev_ts = getattr(ev, 'timestamp', 0)
            if ev_ts < setup_retest_timestamp:
                break
            ev_type = str(getattr(ev, 'event_type', ''))
            ev_dir = str(getattr(ev, 'direction', None) or (ev.metadata.get('direction', '') if hasattr(ev, 'metadata') else ''))
            
            if "LIQUIDITY_SWEEP" in ev_type:
                if is_long and ("BULLISH" in ev_dir or "BUY" in ev_dir or "EQL" in ev_type):
                    sweep_events.append(ev)
                elif not is_long and ("BEARISH" in ev_dir or "SELL" in ev_dir or "EQH" in ev_type):
                    sweep_events.append(ev)

        # Also accept current candle wick rejection of recent extremes if no formal sweep event was emitted
        c = ltf_payload.current_candle
        if not sweep_events:
            # Fall back to checking if current candle made a sweep wick
            if c:
                if is_long and c.close > c.open and (c.open - c.low) > (c.high - c.close):
                    # Bullish hammer/rejection wick
                    sweep_events.append(c)
                elif not is_long and c.close < c.open and (c.high - c.open) > (c.close - c.low):
                    # Bearish shooting star/rejection wick
                    sweep_events.append(c)

        if not sweep_events:
            return EntryEvaluationResult(False, "SWEEP_AND_DISPLACEMENT", "NO_CAUSAL_SWEEP_EVENT", None, None)

        # 2. Check directional displacement
        disp_res = self.displacement_model.evaluate(ltf_payload, required_direction, setup_retest_timestamp)
        if not disp_res.is_confirmed:
            return EntryEvaluationResult(False, "SWEEP_AND_DISPLACEMENT", f"DISPLACEMENT_FAIL_{disp_res.reversal_reason}", None, None)

        # Derive immediate micro invalidation stop
        sweep_extreme = None
        first_ev = sweep_events[0]
        if hasattr(first_ev, 'price_level'):
            sweep_extreme = getattr(first_ev, 'price_level', None)
        elif hasattr(first_ev, 'low') and is_long:
            sweep_extreme = first_ev.low
        elif hasattr(first_ev, 'high') and not is_long:
            sweep_extreme = first_ev.high

        if is_long:
            stop_price = min(c.low, sweep_extreme) if sweep_extreme is not None else c.low
        else:
            stop_price = max(c.high, sweep_extreme) if sweep_extreme is not None else c.high

        return EntryEvaluationResult(
            is_confirmed=True,
            entry_model_name="SWEEP_AND_DISPLACEMENT",
            reversal_reason="CAUSAL_SWEEP_AND_DIRECTIONAL_DISPLACEMENT_CONFIRMED",
            micro_invalidation_price=stop_price,
            entry_price=c.close
        )


class LTFStructuralShiftModel(BaseLTFEntryModel):
    """
    Requires an LTF CHOCH or BOS in the setup direction occurring at or after MTF retest.
    """
    def evaluate(
        self,
        ltf_payload: MarketStatePayload,
        required_direction: str,
        setup_retest_timestamp: int
    ) -> EntryEvaluationResult:
        is_long = required_direction.upper() in ("BULLISH", "LONG", "BUY")
        req_dir = "BULLISH" if is_long else "BEARISH"
        ltf_events = getattr(ltf_payload.structure_state, 'events', None) or ltf_payload.events or []

        for ev in reversed(ltf_events):
            ev_ts = getattr(ev, 'timestamp', 0)
            if ev_ts < setup_retest_timestamp:
                break
            ev_type = str(getattr(ev, 'event_type', ''))
            ev_dir = str(getattr(ev, 'direction', None) or (ev.metadata.get('direction', '') if hasattr(ev, 'metadata') else ''))

            if ("CHOCH" in ev_type or "BOS" in ev_type or "MSS" in ev_type) and req_dir in ev_dir:
                struct = ltf_payload.structure_state
                stop_price = None
                if struct:
                    if is_long and struct.protected_low and struct.protected_low.raw_swing:
                        stop_price = struct.protected_low.raw_swing.price
                    elif not is_long and struct.protected_high and struct.protected_high.raw_swing:
                        stop_price = struct.protected_high.raw_swing.price

                if stop_price is None and ltf_payload.current_candle:
                    stop_price = ltf_payload.current_candle.low if is_long else ltf_payload.current_candle.high

                cur_p = ltf_payload.current_candle.close if ltf_payload.current_candle else ltf_payload.current_price
                return EntryEvaluationResult(
                    is_confirmed=True,
                    entry_model_name="LTF_STRUCTURAL_SHIFT",
                    reversal_reason=f"LTF_{ev_type}_{req_dir}_CONFIRMED",
                    micro_invalidation_price=stop_price,
                    entry_price=cur_p
                )

        return EntryEvaluationResult(False, "LTF_STRUCTURAL_SHIFT", "NO_LTF_STRUCTURAL_SHIFT", None, None)
