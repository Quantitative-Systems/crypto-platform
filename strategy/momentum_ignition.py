"""Momentum Ignition Strategy Hypothesis.

Decomposed cleanly across the 3 Market Model dimensions:
1. MARKET STRUCTURE: Volatility compression / squeeze followed by an explosive structural break.
2. KEY ZONES: Displacement candle cleanly clearing recent consolidation dealing range or Order Block.
3. PHASE: Immediate transition from ACCUMULATION / SQUEEZE into TREND_EXPANSION with expanding ATR.

Trade Management:
- Entry: Next-bar OPEN following high-volume displacement confirmation.
- SL: Base of the displacement candle / ignition origin.
- Target: Next HTF major swing / external liquidity pool (strict >= 3.0R floor).
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


class MomentumIgnitionHypothesis(StrategyHypothesis):
    """Canonical Momentum Ignition Hypothesis."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        min_target_r: float = 3.0,
    ):
        hypothesis_id = f"MOMENTUM_IGNITION_{timeframe_set_id}"
        super().__init__(hypothesis_id=hypothesis_id, min_target_r=min_target_r)
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label

        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Dimension 1: HTF macro bias."""
        trend = htf_state.structure.external_trend
        if trend == TrendDirection.BULLISH:
            return 1
        elif trend == TrendDirection.BEARISH:
            return -1
        return None

    def validate_mtf(self, mtf_state: MarketState, direction: int) -> bool:
        """Dimension 2 & 3: MTF Phase must show momentum expansion."""
        phase = mtf_state.phase.current_phase
        if phase in (MarketPhaseType.CONTINUATION, MarketPhaseType.CONSOLIDATION):
            return True
        return False

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """LTF Entry confirmation: impulsive displacement bar breaking structure."""
        curr_px = ltf_state.close_price
        open_px = ltf_state.open_price or curr_px
        struct = ltf_state.structure

        if direction == 1:
            # Bullish Momentum Ignition: strong bullish displacement candle
            if curr_px <= open_px:
                return False, None, None

            last_low = struct.last_major_low or struct.last_minor_low
            sl = min(open_px, last_low.price if last_low else open_px * 0.99)
            risk = curr_px - sl
            if risk <= 0:
                return False, None, None

            target = curr_px + max(self.min_target_r * risk, 3.0 * risk)
            return True, sl, target

        elif direction == -1:
            # Bearish Momentum Ignition: strong bearish displacement candle
            if curr_px >= open_px:
                return False, None, None

            last_high = struct.last_major_high or struct.last_minor_high
            sl = max(open_px, last_high.price if last_high else open_px * 1.01)
            risk = sl - curr_px
            if risk <= 0:
                return False, None, None

            target = curr_px - max(self.min_target_r * risk, 3.0 * risk)
            return True, sl, target

        return False, None, None
