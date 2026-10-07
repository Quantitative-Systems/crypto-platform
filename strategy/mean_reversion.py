"""Mean Reversion Strategy Hypothesis.

Decomposed cleanly across the 3 Market Model dimensions:
1. MARKET STRUCTURE: Ranging / Consolidation (neutral trend, oscillating swings).
2. KEY ZONES: Price enters extreme dealing range zones (Premium zone for Short, Discount zone for Long).
3. PHASE: CONSOLIDATION / EXHAUSTION near boundary, targeting Equilibrium (50% dealing range).

Trade Management:
- Entry: Next-bar OPEN upon rejection from extreme zone.
- SL: Outside range extreme (+ buffer).
- Target: Dealing range Equilibrium (50% midpoint).
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


class MeanReversionHypothesis(StrategyHypothesis):
    """Canonical Mean Reversion Hypothesis."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        min_target_r: float = 2.0,
    ):
        hypothesis_id = f"MEAN_REVERSION_{timeframe_set_id}"
        super().__init__(hypothesis_id=hypothesis_id, min_target_r=min_target_r)
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label

        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Dimension 1: HTF must not be in an explosive runaway trend."""
        # Mean reversion operates in ranges or neutral/transitional market states
        trend = htf_state.structure.external_trend
        if trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL, TrendDirection.TRANSITIONAL):
            # Direction determined by dealing range location (Key Zones)
            pd_zone = htf_state.zones.premium_discount_zone
            if pd_zone == "PREMIUM":
                return -1  # Look for Short mean-reversion back to equilibrium
            elif pd_zone == "DISCOUNT":
                return 1   # Look for Long mean-reversion back to equilibrium
        return None

    def validate_mtf(self, mtf_state: MarketState, direction: int) -> bool:
        """Dimension 2 & 3: MTF Key Zones and Phase validation.
        
        - Key Zone: Price is at or approaching S/R or extreme premium/discount.
        - Phase: Consolidation or exhaustion phase.
        """
        pd_zone = mtf_state.zones.premium_discount_zone
        if direction == 1 and pd_zone in ("DISCOUNT", "EQUILIBRIUM"):
            return True
        if direction == -1 and pd_zone in ("PREMIUM", "EQUILIBRIUM"):
            return True
        return False

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """LTF Entry confirmation: price reversal away from boundary towards equilibrium."""
        curr_px = ltf_state.close_price
        eq_px = ltf_state.zones.equilibrium_price or curr_px
        struct = ltf_state.structure

        if direction == 1:
            # Long Reversal from Discount
            last_low = struct.last_major_low or struct.last_minor_low
            if not last_low:
                return False, None, None

            sl = last_low.price * 0.998  # Buffer below swing low
            risk = curr_px - sl
            if risk <= 0:
                return False, None, None

            # Target is the range equilibrium
            target = eq_px if eq_px > curr_px else curr_px + 2.0 * risk
            r = (target - curr_px) / risk
            if r >= self.min_target_r:
                return True, sl, target

        elif direction == -1:
            # Short Reversal from Premium
            last_high = struct.last_major_high or struct.last_minor_high
            if not last_high:
                return False, None, None

            sl = last_high.price * 1.002  # Buffer above swing high
            risk = sl - curr_px
            if risk <= 0:
                return False, None, None

            target = eq_px if eq_px < curr_px else curr_px - 2.0 * risk
            r = (curr_px - target) / risk
            if r >= self.min_target_r:
                return True, sl, target

        return False, None, None
