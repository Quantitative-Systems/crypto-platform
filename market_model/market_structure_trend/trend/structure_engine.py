"""Market Structure & Trend Primitives Engine.

Calculates external and internal market structure, swing hierarchies,
BOS, CHoCH, MSS, protected vs. weak swings, and trend state causally without lookahead.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np

from market_model.contracts import (
    StructuralBreak,
    StructuralBreakType,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
)


class StructureEngine:
    """Causal, timeframe-aware engine for detecting swings, structure, and structural transitions."""

    def __init__(
        self,
        timeframe: str = "1D",
        major_left: int = 4,
        major_right: int = 4,
        minor_left: int = 2,
        minor_right: int = 2,
    ):
        self.timeframe = timeframe
        self.major_left = major_left
        self.major_right = major_right
        self.minor_left = minor_left
        self.minor_right = minor_right

    def detect_swings(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        timestamps: np.ndarray,
        left: int,
        right: int,
        level_type: str = "MAJOR",
    ) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Detect swing points causally up to bar n-1.
        
        A swing at bar i is confirmed only when bar i + right has closed.
        Hence, no swing can be detected beyond index n - right - 1.
        """
        n = len(highs)
        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []

        if n < left + right + 1:
            return swing_highs, swing_lows

        for i in range(left, n - right):
            # Swing High Check
            h_val = highs[i]
            is_sh = True
            for l_idx in range(i - left, i):
                if highs[l_idx] >= h_val:
                    is_sh = False
                    break
            if is_sh:
                for r_idx in range(i + 1, i + right + 1):
                    if highs[r_idx] > h_val:
                        is_sh = False
                        break

            if is_sh:
                swing_highs.append(
                    SwingPoint(
                        timestamp_ms=int(timestamps[i]),
                        price=float(h_val),
                        is_high=True,
                        level_type=level_type,
                        bar_index=i,
                    )
                )

            # Swing Low Check
            l_val = lows[i]
            is_sl = True
            for l_idx in range(i - left, i):
                if lows[l_idx] <= l_val:
                    is_sl = False
                    break
            if is_sl:
                for r_idx in range(i + 1, i + right + 1):
                    if lows[r_idx] < l_val:
                        is_sl = False
                        break

            if is_sl:
                swing_lows.append(
                    SwingPoint(
                        timestamp_ms=int(timestamps[i]),
                        price=float(l_val),
                        is_high=False,
                        level_type=level_type,
                        bar_index=i,
                    )
                )

        return swing_highs, swing_lows

    def compute_structure(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
    ) -> StructureSnapshot:
        """Compute complete StructureSnapshot causally as of the last closed bar."""
        n = len(closes)
        if n == 0:
            return StructureSnapshot()

        # 1. Detect External (Major) and Internal (Minor) swings
        maj_highs, maj_lows = self.detect_swings(
            highs, lows, timestamps, self.major_left, self.major_right, "MAJOR"
        )
        min_highs, min_lows = self.detect_swings(
            highs, lows, timestamps, self.minor_left, self.minor_right, "MINOR"
        )

        last_maj_h = maj_highs[-1] if maj_highs else None
        last_maj_l = maj_lows[-1] if maj_lows else None
        last_min_h = min_highs[-1] if min_highs else None
        last_min_l = min_lows[-1] if min_lows else None

        # 2. External Trend Classification (HH/HL vs LH/LL)
        ext_trend = TrendDirection.NEUTRAL
        if len(maj_highs) >= 2 and len(maj_lows) >= 2:
            hh = maj_highs[-1].price > maj_highs[-2].price
            hl = maj_lows[-1].price > maj_lows[-2].price
            lh = maj_highs[-1].price < maj_highs[-2].price
            ll = maj_lows[-1].price < maj_lows[-2].price

            if hh and hl:
                ext_trend = TrendDirection.BULLISH
            elif lh and ll:
                ext_trend = TrendDirection.BEARISH
            elif hh and not hl:
                ext_trend = TrendDirection.TRANSITIONAL
            elif ll and not lh:
                ext_trend = TrendDirection.TRANSITIONAL
            else:
                ext_trend = TrendDirection.RANGE
        elif len(maj_highs) >= 1 and len(maj_lows) >= 1:
            if maj_highs[-1].bar_index > maj_lows[-1].bar_index:
                ext_trend = TrendDirection.BULLISH
            else:
                ext_trend = TrendDirection.BEARISH

        # 3. Internal Trend Classification
        int_trend = TrendDirection.NEUTRAL
        if len(min_highs) >= 2 and len(min_lows) >= 2:
            min_hh = min_highs[-1].price > min_highs[-2].price
            min_hl = min_lows[-1].price > min_lows[-2].price
            min_lh = min_highs[-1].price < min_highs[-2].price
            min_ll = min_lows[-1].price < min_lows[-2].price

            if min_hh and min_hl:
                int_trend = TrendDirection.BULLISH
            elif min_lh and min_ll:
                int_trend = TrendDirection.BEARISH
            else:
                int_trend = TrendDirection.RANGE

        # 4. Structural Breaks & Transitions (BOS vs CHOCH)
        curr_close = closes[-1]
        curr_ts = int(timestamps[-1])
        breaks: List[StructuralBreak] = []

        if ext_trend == TrendDirection.BULLISH:
            if last_maj_h and curr_close > last_maj_h.price:
                breaks.append(
                    StructuralBreak(
                        timestamp_ms=curr_ts,
                        break_type=StructuralBreakType.BOS_BULLISH,
                        trigger_price=float(curr_close),
                        broken_swing_price=last_maj_h.price,
                        is_internal=False,
                    )
                )
            if last_maj_l and curr_close < last_maj_l.price:
                breaks.append(
                    StructuralBreak(
                        timestamp_ms=curr_ts,
                        break_type=StructuralBreakType.CHOCH_BEARISH,
                        trigger_price=float(curr_close),
                        broken_swing_price=last_maj_l.price,
                        is_internal=False,
                    )
                )

        elif ext_trend == TrendDirection.BEARISH:
            if last_maj_l and curr_close < last_maj_l.price:
                breaks.append(
                    StructuralBreak(
                        timestamp_ms=curr_ts,
                        break_type=StructuralBreakType.BOS_BEARISH,
                        trigger_price=float(curr_close),
                        broken_swing_price=last_maj_l.price,
                        is_internal=False,
                    )
                )
            if last_maj_h and curr_close > last_maj_h.price:
                breaks.append(
                    StructuralBreak(
                        timestamp_ms=curr_ts,
                        break_type=StructuralBreakType.CHOCH_BULLISH,
                        trigger_price=float(curr_close),
                        broken_swing_price=last_maj_h.price,
                        is_internal=False,
                    )
                )

        # Internal breaks (minor CHOCH / BOS)
        if last_min_h and curr_close > last_min_h.price:
            breaks.append(
                StructuralBreak(
                    timestamp_ms=curr_ts,
                    break_type=StructuralBreakType.CHOCH_BULLISH if ext_trend == TrendDirection.BEARISH else StructuralBreakType.BOS_BULLISH,
                    trigger_price=float(curr_close),
                    broken_swing_price=last_min_h.price,
                    is_internal=True,
                )
            )
        elif last_min_l and curr_close < last_min_l.price:
            breaks.append(
                StructuralBreak(
                    timestamp_ms=curr_ts,
                    break_type=StructuralBreakType.CHOCH_BEARISH if ext_trend == TrendDirection.BULLISH else StructuralBreakType.BOS_BEARISH,
                    trigger_price=float(curr_close),
                    broken_swing_price=last_min_l.price,
                    is_internal=True,
                )
            )

        # 5. Protected vs. Weak Structure
        # In Bullish trend: the major low is protected; the major high is the weak target to be taken out.
        # In Bearish trend: the major high is protected; the major low is the weak target to be taken out.
        protected_high = last_maj_h.price if ext_trend == TrendDirection.BEARISH and last_maj_h else None
        protected_low = last_maj_l.price if ext_trend == TrendDirection.BULLISH and last_maj_l else None
        weak_high = last_maj_h.price if ext_trend == TrendDirection.BULLISH and last_maj_h else None
        weak_low = last_maj_l.price if ext_trend == TrendDirection.BEARISH and last_maj_l else None

        if last_maj_l and protected_low:
            last_maj_l.is_protected = True
        if last_maj_h and protected_high:
            last_maj_h.is_protected = True
        if last_maj_h and weak_high:
            last_maj_h.is_weak = True
        if last_maj_l and weak_low:
            last_maj_l.is_weak = True

        trend_strength = 1.0 if ext_trend in (TrendDirection.BULLISH, TrendDirection.BEARISH) else 0.0

        return StructureSnapshot(
            external_trend=ext_trend,
            internal_trend=int_trend,
            last_major_high=last_maj_h,
            last_major_low=last_maj_l,
            last_minor_high=last_min_h,
            last_minor_low=last_min_l,
            recent_breaks=breaks,
            protected_high=protected_high,
            protected_low=protected_low,
            weak_high=weak_high,
            weak_low=weak_low,
            trend_strength=trend_strength,
        )
