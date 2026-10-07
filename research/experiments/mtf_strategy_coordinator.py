"""Canonical Multi-Timeframe Research Strategy Coordinator.

Implements the HTF -> MTF -> LTF causal decision pipeline across any timeframe set:
1. HTF = Bias & Conditional Hypothesis (HYP_A_PULLBACK vs. HYP_B_CONTINUATION)
2. MTF = Hypothesis Validation (Zone interaction + structural alignment)
3. LTF = Precise Entry Confirmation & Initial Structural SL
4. Management = MTF Structural Trailing Stop + HTF Target Objective
5. Strict Floor = Target R >= 4.0 (Reject if < 4R)
6. Risk Limit = 1.0% account risk per trade
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreakType,
    TrendDirection,
)
from market_model.state_generator import MarketStateGenerator


class MTFStrategyCoordinator:
    """Coordinates HTF -> MTF -> LTF hypothesis evaluation causally over time."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        hypothesis_type: str = "CONTINUATION",  # "PULLBACK" or "CONTINUATION"
        min_target_r: float = 4.0,
    ):
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label
        self.hypothesis_type = hypothesis_type.upper()  # PULLBACK or CONTINUATION
        self.min_target_r = min_target_r

        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def scan_signals(
        self,
        symbol: str,
        htf_data: Dict[str, np.ndarray],
        mtf_data: Dict[str, np.ndarray],
        ltf_data: Dict[str, np.ndarray],
    ) -> Tuple[List[Dict[str, Any]], Dict[int, float]]:
        """Causally evaluate signals at every LTF bar using only closed HTF and MTF bars.
        
        Returns:
            candidates: List of trade candidates ready for backtest execution.
            mtf_trailing_map: Map of LTF timestamp -> MTF trailing stop price.
        """
        ltf_closes = ltf_data["c"]
        ltf_ts = ltf_data["ts"]
        n_ltf = len(ltf_closes)

        htf_close_ts = htf_data["close_ts"]
        mtf_close_ts = mtf_data["close_ts"]

        candidates: List[Dict[str, Any]] = []
        mtf_trailing_map: Dict[int, float] = {}

        # Pre-align HTF and MTF indices causally to LTF open/close timestamps
        # At LTF bar i (open at ltf_ts[i]), only HTF/MTF bars with close_ts <= ltf_ts[i] are known!
        htf_ptr = 0
        mtf_ptr = 0

        # Optimization: cache last known HTF and MTF MarketState to avoid recalculating every bar
        last_htf_state: Optional[MarketState] = None
        last_htf_idx = -1

        last_mtf_state: Optional[MarketState] = None
        last_mtf_idx = -1

        # Minimum warmup bars
        warmup = max(60, 50)

        for i in range(warmup, n_ltf):
            t_curr = ltf_ts[i]

            # 1. Identify last closed HTF bar
            htf_idx = np.searchsorted(htf_close_ts, t_curr, side="right") - 1
            if htf_idx < 30:
                continue

            if htf_idx != last_htf_idx:
                htf_start = max(0, htf_idx - 250)
                last_htf_state = self.htf_gen.generate(
                    symbol=symbol,
                    opens=htf_data["o"][htf_start : htf_idx + 1],
                    highs=htf_data["h"][htf_start : htf_idx + 1],
                    lows=htf_data["l"][htf_start : htf_idx + 1],
                    closes=htf_data["c"][htf_start : htf_idx + 1],
                    volumes=htf_data["v"][htf_start : htf_idx + 1],
                    timestamps=htf_data["ts"][htf_start : htf_idx + 1],
                )
                last_htf_idx = htf_idx

            htf_state = last_htf_state
            if htf_state is None:
                continue

            # 2. HTF Bias & Conditional Hypothesis Evaluation
            htf_trend = htf_state.structure.external_trend
            htf_phase = htf_state.phase.current_phase

            if htf_trend not in (TrendDirection.BULLISH, TrendDirection.BEARISH):
                continue

            # Check Hypothesis Match:
            # HYP_B_CONTINUATION: HTF is in trend, searching for pullback resolution into continuation
            # HYP_A_PULLBACK: HTF is in trend, searching for the initial pullback impulse
            is_continuation_hyp = self.hypothesis_type == "CONTINUATION"
            is_pullback_hyp = self.hypothesis_type == "PULLBACK"

            if is_continuation_hyp:
                # Expected: HTF is Bullish/Bearish, and has completed or is in pullback
                expected_dir = 1 if htf_trend == TrendDirection.BULLISH else -1
            elif is_pullback_hyp:
                # Expected: counter-trend pullback move
                expected_dir = -1 if htf_trend == TrendDirection.BULLISH else 1
            else:
                continue

            # 3. Identify last closed MTF bar
            mtf_idx = np.searchsorted(mtf_close_ts, t_curr, side="right") - 1
            if mtf_idx < 25:
                continue

            if mtf_idx != last_mtf_idx:
                mtf_start = max(0, mtf_idx - 250)
                last_mtf_state = self.mtf_gen.generate(
                    symbol=symbol,
                    opens=mtf_data["o"][mtf_start : mtf_idx + 1],
                    highs=mtf_data["h"][mtf_start : mtf_idx + 1],
                    lows=mtf_data["l"][mtf_start : mtf_idx + 1],
                    closes=mtf_data["c"][mtf_start : mtf_idx + 1],
                    volumes=mtf_data["v"][mtf_start : mtf_idx + 1],
                    timestamps=mtf_data["ts"][mtf_start : mtf_idx + 1],
                )
                last_mtf_idx = mtf_idx

            mtf_state = last_mtf_state
            if mtf_state is None:
                continue

            # Track MTF trailing level for open trade management
            if expected_dir == 1 and mtf_state.structure.last_major_low:
                mtf_trailing_map[t_curr] = mtf_state.structure.last_major_low.price
            elif expected_dir == -1 and mtf_state.structure.last_major_high:
                mtf_trailing_map[t_curr] = mtf_state.structure.last_major_high.price

            # 4. MTF Validation Check
            # For Continuation: MTF price must be in Discount (for long) or Premium (for short)
            # OR interacting with an active MTF KeyZone (OB / FVG)
            mtf_pd = mtf_state.zones.premium_discount_zone
            mtf_valid = False

            if expected_dir == 1:
                if mtf_pd == "DISCOUNT" or len(mtf_state.zones.fair_value_gaps) > 0:
                    mtf_valid = True
            elif expected_dir == -1:
                if mtf_pd == "PREMIUM" or len(mtf_state.zones.fair_value_gaps) > 0:
                    mtf_valid = True

            if not mtf_valid:
                continue

            # 5. LTF Precise Entry Confirmation (Zero Lookahead on LTF)
            # Evaluate LTF structure over recent 30-50 bars
            ltf_start = max(0, i - 40)
            ltf_sub_o = ltf_data["o"][ltf_start : i + 1]
            ltf_sub_h = ltf_data["h"][ltf_start : i + 1]
            ltf_sub_l = ltf_data["l"][ltf_start : i + 1]
            ltf_sub_c = ltf_data["c"][ltf_start : i + 1]
            ltf_sub_v = ltf_data["v"][ltf_start : i + 1]
            ltf_sub_ts = ltf_data["ts"][ltf_start : i + 1]

            ltf_state = self.ltf_gen.generate(
                symbol=symbol,
                opens=ltf_sub_o,
                highs=ltf_sub_h,
                lows=ltf_sub_l,
                closes=ltf_sub_c,
                volumes=ltf_sub_v,
                timestamps=ltf_sub_ts,
            )

            # Look for recent LTF structural break in direction of hypothesis
            ltf_breaks = ltf_state.structure.recent_breaks
            if not ltf_breaks:
                continue

            last_break = ltf_breaks[-1]
            is_confirmed = False

            if expected_dir == 1:
                if last_break.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH):
                    is_confirmed = True
            elif expected_dir == -1:
                if last_break.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH):
                    is_confirmed = True

            if not is_confirmed:
                continue

            # 6. Establish Initial SL and HTF Destination Target
            curr_px = float(ltf_closes[i])

            if expected_dir == 1:
                # SL at recent LTF swing low or ATR boundary
                sl_ref = ltf_state.structure.last_minor_low or ltf_state.structure.last_major_low
                if sl_ref and sl_ref.price < curr_px:
                    initial_sl = sl_ref.price * 0.999
                else:
                    initial_sl = curr_px - ltf_state.measurements.atr * 2.0

                # Target at HTF weak high or opposing zone (MUST be strictly above current price)
                if is_continuation_hyp and htf_state.structure.weak_high and htf_state.structure.weak_high > curr_px:
                    target_px = htf_state.structure.weak_high
                elif htf_state.zones.previous_high and htf_state.zones.previous_high > curr_px:
                    target_px = htf_state.zones.previous_high
                else:
                    target_px = curr_px + 4.5 * abs(curr_px - initial_sl)

                risk_dist = curr_px - initial_sl
                reward_dist = target_px - curr_px

            else:
                sl_ref = ltf_state.structure.last_minor_high or ltf_state.structure.last_major_high
                if sl_ref and sl_ref.price > curr_px:
                    initial_sl = sl_ref.price * 1.001
                else:
                    initial_sl = curr_px + ltf_state.measurements.atr * 2.0

                # Target at HTF weak low or opposing zone (MUST be strictly below current price)
                if is_continuation_hyp and htf_state.structure.weak_low and htf_state.structure.weak_low < curr_px:
                    target_px = htf_state.structure.weak_low
                elif htf_state.zones.previous_low and htf_state.zones.previous_low < curr_px:
                    target_px = htf_state.zones.previous_low
                else:
                    target_px = curr_px - 4.5 * abs(curr_px - initial_sl)

                risk_dist = initial_sl - curr_px
                reward_dist = curr_px - target_px

            if risk_dist <= 0 or reward_dist <= 0:
                continue

            proposed_r = reward_dist / risk_dist

            # STRICT MINIMUM 4R REQUIREMENT: < 4R = REJECT
            if proposed_r < self.min_target_r:
                # Check if target can be adjusted to HTF extension; if not, reject
                continue

            candidates.append(
                {
                    "bar_index": i,
                    "direction": expected_dir,
                    "entry_price": curr_px,
                    "stop_price": initial_sl,
                    "target_price": target_px,
                    "target_r": proposed_r,
                    "meta": {
                        "htf_trend": htf_trend.value,
                        "mtf_pd": mtf_pd,
                        "break_type": last_break.break_type.value,
                    },
                }
            )

        return candidates, mtf_trailing_map
