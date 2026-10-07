"""Base Strategy Family Implementation.

Provides common causal multi-timeframe coordination:
- HTF directional hypothesis formulation (Pullback vs Continuation)
- MTF setup validation
- LTF causal execution trigger (BOS / CHoCH / Structural breakout)
- LTF initial structural invalidation (SL)
- MTF monotonic structural trailing stop
- HTF destination target (enforcing strictly >= 4.0R floor)
- 1% account risk sizing: risk_amount / stop_distance
"""
from __future__ import annotations

from abc import abstractmethod
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


class BaseStrategyFamily(StrategyHypothesis):
    """Base class for all Phase A Strategy Discovery families."""

    def __init__(
        self,
        family_id: str,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        phase_mode: str = "PULLBACK",  # "PULLBACK" or "CONTINUATION"
        min_target_r: float = 4.0,
        risk_pct_per_trade: float = 0.01,
    ):
        hypothesis_id = f"{family_id}_{phase_mode.upper()}_{timeframe_set_id}"
        super().__init__(hypothesis_id=hypothesis_id, min_target_r=min_target_r)
        self.family_id = family_id
        self.timeframe_set_id = timeframe_set_id
        self.htf_label = htf_label
        self.mtf_label = mtf_label
        self.ltf_label = ltf_label
        self.phase_mode = phase_mode.upper()
        self.risk_pct_per_trade = risk_pct_per_trade

        # Causal timeframe state generators
        self.htf_gen = MarketStateGenerator(timeframe=htf_label)
        self.mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        self.ltf_gen = MarketStateGenerator(timeframe=ltf_label)

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Formulate HTF conditional bias based on Structure and Phase."""
        trend = htf_state.structure.external_trend
        if trend == TrendDirection.BULLISH:
            return 1
        elif trend == TrendDirection.BEARISH:
            return -1
        return None

    @abstractmethod
    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Family-specific MTF observation validation (Zone, EMA, OB, FVG, etc.)."""
        pass

    def validate_mtf(self, mtf_state: MarketState, direction: int) -> bool:
        """Validate MTF phase alignment and family-specific evidence."""
        curr_phase = mtf_state.phase.current_phase
        if self.phase_mode == "PULLBACK":
            # For pullback, MTF should be in pullback or transitioning
            if curr_phase not in (MarketPhaseType.PULLBACK, MarketPhaseType.CONSOLIDATION):
                return False
        elif self.phase_mode == "CONTINUATION":
            # For continuation, MTF should be in continuation or expansion
            if curr_phase not in (MarketPhaseType.CONTINUATION, MarketPhaseType.CONSOLIDATION):
                return False

        return self.validate_mtf_family_specifics(mtf_state, direction)

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """LTF causal entry confirmation via structural break (BOS / CHoCH) and >= 4R target."""
        curr_px = ltf_state.close_price
        struct = ltf_state.structure

        if direction == 1:
            # Bullish: require bullish break or swing confirmation
            has_break = any(
                b.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH, StructuralBreakType.MSS_BULLISH)
                for b in struct.recent_breaks[-3:]
            ) if struct.recent_breaks else False

            # Fallback to local price action: close above recent swing high
            if not has_break and struct.last_minor_high:
                has_break = curr_px > struct.last_minor_high.price

            if not has_break:
                return False, None, None

            # Local structural invalidation (SL)
            last_low = struct.last_minor_low or struct.last_major_low
            if not last_low:
                return False, None, None

            sl = last_low.price * 0.999  # Tight structural buffer
            risk = curr_px - sl
            if risk <= 0:
                return False, None, None

            # Target: HTF major swing or expansion objective
            target = curr_px + max(self.min_target_r * risk, 4.0 * risk)
            return True, sl, target

        elif direction == -1:
            # Bearish: require bearish break or swing confirmation
            has_break = any(
                b.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH, StructuralBreakType.MSS_BEARISH)
                for b in struct.recent_breaks[-3:]
            ) if struct.recent_breaks else False

            if not has_break and struct.last_minor_low:
                has_break = curr_px < struct.last_minor_low.price

            if not has_break:
                return False, None, None

            last_high = struct.last_minor_high or struct.last_major_high
            if not last_high:
                return False, None, None

            sl = last_high.price * 1.001
            risk = sl - curr_px
            if risk <= 0:
                return False, None, None

            target = curr_px - max(self.min_target_r * risk, 4.0 * risk)
            return True, sl, target

        return False, None, None
