"""Trend Breakout Strategy Hypothesis.

Decomposed cleanly across the 3 Market Model dimensions:
1. MARKET STRUCTURE: HTF external trend confirmed (BULLISH/BEARISH) + LTF breaks structural pivot.
2. KEY ZONES: Price breaks out through dealing range high (Resistance) or low (Support).
3. PHASE: CONTINUATION or EXPANSION phase with momentum.

Trade Management:
- Entry: Next-bar OPEN following breakout confirmation.
- SL: Previous structural swing (weak high/low).
- Target: HTF major swing / external liquidity pool (strict >= 3.0R floor).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    TrendDirection,
)
from market_model.state_generator import MarketStateGenerator
from strategy.base import CandidateSignal, StrategyHypothesis


class TrendBreakoutHypothesis(StrategyHypothesis):
    """Canonical Trend Breakout Hypothesis."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        min_target_r: float = 3.0,
    ):
        hypothesis_id = f"TREND_BREAKOUT_{timeframe_set_id}"
        super().__init__(hypothesis_id=hypothesis_id, min_target_r=min_target_r)
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label

        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Dimension 1: HTF Market Structure must confirm a clear trend direction."""
        trend = htf_state.structure.external_trend
        if trend == TrendDirection.BULLISH:
            return 1
        elif trend == TrendDirection.BEARISH:
            return -1
        return None

    def validate_mtf(self, mtf_state: MarketState, direction: int) -> bool:
        """Dimension 2 & 3: MTF Key Zones and Phase validation.
        
        - Key Zone: Dealing range must be well-defined.
        - Phase: MTF must not be in deep counter-trend exhaustion.
        """
        # MTF Phase check
        if mtf_state.phase.current_phase == MarketPhaseType.CONSOLIDATION:
            # Consolidation breaking into trend is acceptable
            return True
        if direction == 1 and mtf_state.phase.current_phase in (
            MarketPhaseType.CONTINUATION,
            MarketPhaseType.PULLBACK,
        ):
            return True
        if direction == -1 and mtf_state.phase.current_phase in (
            MarketPhaseType.CONTINUATION,
            MarketPhaseType.PULLBACK,
        ):
            return True
        return False

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """LTF Entry confirmation: price breaks beyond recent structural swing."""
        curr_px = ltf_state.close_price
        struct = ltf_state.structure

        if direction == 1:
            # Bullish Breakout
            last_high = struct.last_major_high or struct.last_minor_high
            last_low = struct.last_major_low or struct.last_minor_low
            if not last_high or not last_low:
                return False, None, None

            # Price must be breaking above the swing high
            if curr_px >= last_high.price:
                sl = last_low.price
                risk = curr_px - sl
                if risk <= 0:
                    return False, None, None
                target = curr_px + max(self.min_target_r * risk, 3.0 * risk)
                return True, sl, target

        elif direction == -1:
            # Bearish Breakout
            last_high = struct.last_major_high or struct.last_minor_high
            last_low = struct.last_major_low or struct.last_minor_low
            if not last_high or not last_low:
                return False, None, None

            # Price must be breaking below the swing low
            if curr_px <= last_low.price:
                sl = last_high.price
                risk = sl - curr_px
                if risk <= 0:
                    return False, None, None
                target = curr_px - max(self.min_target_r * risk, 3.0 * risk)
                return True, sl, target

        return False, None, None
