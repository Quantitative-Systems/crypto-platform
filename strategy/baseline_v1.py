"""BASELINE STRATEGY / HYPOTHESIS V1.

Explicitly named and separated from the underlying Market Model.

This is ONE particular strategy hypothesis among many:
- HTF Hypothesis: Conditional Directional Bias (Pullback vs Continuation)
- MTF Validation: Dealing Range Discount/Premium + Active Key Zone (OB/FVG) Interaction
- LTF Entry: Structural Break (BOS / CHoCH) Confirmation
- LTF SL: Local structural invalidation (minor swing low/high)
- MTF Trailing: Monotonic MTF structural trailing stop
- HTF Target: HTF weak structure or opposing zone destination (Strict floor >= 4.0R)

The Market Model does NOT require any of these components as universal truths.
They are specific candidate rules under test in Baseline V1.
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
from strategy.base import CandidateSignal, StrategyHypothesis


class BaselineStrategyHypothesisV1(StrategyHypothesis):
    """Canonical implementation of BASELINE STRATEGY / HYPOTHESIS V1."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        hypothesis_type: str = "CONTINUATION",  # "PULLBACK" or "CONTINUATION"
        min_target_r: float = 4.0,
    ):
        hypothesis_id = f"BASELINE_V1_{hypothesis_type.upper()}_{timeframe_set_id}"
        super().__init__(hypothesis_id=hypothesis_id, min_target_r=min_target_r)
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label
        self.hypothesis_type = hypothesis_type.upper()

        # Pure strategy-agnostic MarketState generators
        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Formulate a conditional directional hypothesis from HTF MarketState."""
        htf_trend = htf_state.structure.external_trend
        if htf_trend not in (TrendDirection.BULLISH, TrendDirection.BEARISH):
            return None

        if self.hypothesis_type == "CONTINUATION":
            return 1 if htf_trend == TrendDirection.BULLISH else -1
        elif self.hypothesis_type == "PULLBACK":
            return -1 if htf_trend == TrendDirection.BULLISH else 1
        return None

    def validate_mtf(self, mtf_state: MarketState, direction: int) -> bool:
        """Determine whether MTF price behavior validates the HTF hypothesis."""
        pd_zone = mtf_state.zones.premium_discount_zone
        has_fvg = len(mtf_state.zones.fair_value_gaps) > 0

        if direction == 1:
            return pd_zone == "DISCOUNT" or has_fvg
        elif direction == -1:
            return pd_zone == "PREMIUM" or has_fvg
        return False

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """Evaluate LTF precise confirmation and derive initial SL and target."""
        recent_breaks = ltf_state.structure.recent_breaks
        if not recent_breaks:
            return False, None, None

        last_break = recent_breaks[-1]
        is_confirmed = False

        if direction == 1:
            if last_break.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH):
                is_confirmed = True
        elif direction == -1:
            if last_break.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH):
                is_confirmed = True

        if not is_confirmed:
            return False, None, None

        curr_px = ltf_state.close_price

        if direction == 1:
            sl_ref = ltf_state.structure.last_minor_low or ltf_state.structure.last_major_low
            initial_sl = (sl_ref.price * 0.999) if (sl_ref and sl_ref.price < curr_px) else (curr_px - ltf_state.measurements.atr * 2.0)
            target_px = curr_px + 4.5 * abs(curr_px - initial_sl)
        else:
            sl_ref = ltf_state.structure.last_minor_high or ltf_state.structure.last_major_high
            initial_sl = (sl_ref.price * 1.001) if (sl_ref and sl_ref.price > curr_px) else (curr_px + ltf_state.measurements.atr * 2.0)
            target_px = curr_px - 4.5 * abs(curr_px - initial_sl)

        return True, initial_sl, target_px

    def scan_signals(
        self,
        symbol: str,
        htf_data: Dict[str, np.ndarray],
        mtf_data: Dict[str, np.ndarray],
        ltf_data: Dict[str, np.ndarray],
    ) -> Tuple[List[CandidateSignal], Dict[int, float]]:
        """Causally evaluate signals at every LTF bar using only closed HTF and MTF bars."""
        ltf_closes = ltf_data["c"]
        ltf_ts = ltf_data["ts"]
        n_ltf = len(ltf_closes)

        htf_close_ts = htf_data["close_ts"]
        mtf_close_ts = mtf_data["close_ts"]

        candidates: List[CandidateSignal] = []
        mtf_trailing_map: Dict[int, float] = {}

        last_htf_state: Optional[MarketState] = None
        last_htf_idx = -1
        last_mtf_state: Optional[MarketState] = None
        last_mtf_idx = -1

        warmup = 60

        for i in range(warmup, n_ltf):
            t_curr = ltf_ts[i]

            # 1. Closed HTF bar
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

            direction = self.evaluate_htf(htf_state)
            if direction is None:
                continue

            # 2. Closed MTF bar
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

            # Track MTF trailing level
            if direction == 1 and mtf_state.structure.last_major_low:
                mtf_trailing_map[t_curr] = mtf_state.structure.last_major_low.price
            elif direction == -1 and mtf_state.structure.last_major_high:
                mtf_trailing_map[t_curr] = mtf_state.structure.last_major_high.price

            # MTF Validation
            if not self.validate_mtf(mtf_state, direction):
                continue

            # 3. LTF Precise Entry Confirmation
            ltf_start = max(0, i - 50)
            ltf_state = self.ltf_gen.generate(
                symbol=symbol,
                opens=ltf_data["o"][ltf_start : i + 1],
                highs=ltf_data["h"][ltf_start : i + 1],
                lows=ltf_data["l"][ltf_start : i + 1],
                closes=ltf_data["c"][ltf_start : i + 1],
                volumes=ltf_data["v"][ltf_start : i + 1],
                timestamps=ltf_data["ts"][ltf_start : i + 1],
            )

            confirmed, initial_sl, target_px = self.confirm_ltf_entry(ltf_state, direction)
            if not confirmed or initial_sl is None or target_px is None:
                continue

            curr_px = float(ltf_closes[i])
            risk_dist = abs(curr_px - initial_sl)
            reward_dist = abs(target_px - curr_px)
            if risk_dist <= 0:
                continue

            proposed_r = reward_dist / risk_dist
            if proposed_r < self.min_target_r:
                continue

            candidates.append(
                CandidateSignal(
                    bar_index=i,
                    direction=direction,
                    entry_price=curr_px,
                    stop_price=initial_sl,
                    target_price=target_px,
                    target_r=proposed_r,
                    hypothesis_id=self.hypothesis_id,
                    meta={
                        "htf_trend": htf_state.structure.external_trend.value,
                        "mtf_pd": mtf_state.zones.premium_discount_zone,
                    },
                )
            )

        return candidates, mtf_trailing_map
