"""Market Phase Classification Engine.

Classifies market state strictly into PULLBACK or CONTINUATION across both
External and Internal structural dimensions, and computes phase characteristics
(depth, duration, displacement, compression) causally.
"""
from __future__ import annotations

import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    PhaseSnapshot,
    StructureSnapshot,
    TrendDirection,
)


class PhaseEngine:
    """Causal engine for detecting and classifying External and Internal Market Phases."""

    def compute_phase(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        structure: StructureSnapshot,
    ) -> PhaseSnapshot:
        """Classify market phase relative to current structural snapshot."""
        n = len(closes)
        if n < 5 or structure.external_trend == TrendDirection.NEUTRAL:
            return PhaseSnapshot(
                external_phase=MarketPhaseType.UNCERTAIN,
                internal_phase=MarketPhaseType.UNCERTAIN,
                current_phase=MarketPhaseType.UNCERTAIN,
            )

        curr_close = float(closes[-1])
        ext_trend = structure.external_trend
        int_trend = structure.internal_trend

        ext_phase = MarketPhaseType.UNCERTAIN
        int_phase = MarketPhaseType.UNCERTAIN
        depth_pct = 0.0
        duration_bars = 0
        is_displaced = False
        is_compressed = False

        # ---------------------------------------------------------------------
        # 1. External Phase Classification
        # ---------------------------------------------------------------------
        if ext_trend == TrendDirection.BULLISH:
            if structure.last_major_high and curr_close < structure.last_major_high.price:
                # Retracing downwards inside bullish structure -> PULLBACK
                ext_phase = MarketPhaseType.PULLBACK
                depth_pct = (
                    (structure.last_major_high.price - curr_close)
                    / structure.last_major_high.price
                    * 100.0
                )
                duration_bars = max(1, n - 1 - structure.last_major_high.bar_index)
            elif structure.last_major_high and curr_close >= structure.last_major_high.price:
                # Expanding above previous major high -> CONTINUATION
                ext_phase = MarketPhaseType.CONTINUATION
                is_displaced = True
                duration_bars = 3

        elif ext_trend == TrendDirection.BEARISH:
            if structure.last_major_low and curr_close > structure.last_major_low.price:
                # Retracing upwards inside bearish structure -> PULLBACK
                ext_phase = MarketPhaseType.PULLBACK
                depth_pct = (
                    (curr_close - structure.last_major_low.price)
                    / structure.last_major_low.price
                    * 100.0
                )
                duration_bars = max(1, n - 1 - structure.last_major_low.bar_index)
            elif structure.last_major_low and curr_close <= structure.last_major_low.price:
                # Expanding below previous major low -> CONTINUATION
                ext_phase = MarketPhaseType.CONTINUATION
                is_displaced = True
                duration_bars = 3

        # ---------------------------------------------------------------------
        # 2. Internal Phase Classification (Fractal sub-structure)
        # ---------------------------------------------------------------------
        if ext_phase == MarketPhaseType.PULLBACK:
            # During an external pullback:
            # If internal trend is aligned with external trend -> internal phase is transitioning to CONTINUATION
            # If internal trend is counter to external trend -> internal phase is still PULLBACK
            if ext_trend == TrendDirection.BULLISH:
                if int_trend == TrendDirection.BULLISH:
                    int_phase = MarketPhaseType.CONTINUATION
                else:
                    int_phase = MarketPhaseType.PULLBACK
            elif ext_trend == TrendDirection.BEARISH:
                if int_trend == TrendDirection.BEARISH:
                    int_phase = MarketPhaseType.CONTINUATION
                else:
                    int_phase = MarketPhaseType.PULLBACK
        else:
            int_phase = ext_phase

        # Measure compression (small range bars)
        if n >= 5:
            recent_ranges = highs[-5:] - lows[-5:]
            avg_range = float(np.mean(recent_ranges))
            if recent_ranges[-1] < avg_range * 0.6:
                is_compressed = True

        primary_phase = ext_phase if ext_phase != MarketPhaseType.UNCERTAIN else int_phase

        return PhaseSnapshot(
            external_phase=ext_phase,
            internal_phase=int_phase,
            current_phase=primary_phase,
            depth_pct=round(depth_pct, 2),
            duration_bars=duration_bars,
            is_compressed=is_compressed,
            is_displaced=is_displaced,
        )
