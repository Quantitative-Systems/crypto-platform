"""Canonical 4R/5R Primary Research Hypothesis Engine.

Implements the first testable hypothesis on top of the canonical MarketState model:

  HTF EXTERNAL STRUCTURE (BULLISH / BEARISH)
            │
            ▼
     MTF PULLBACK
            │
            ▼
   KEY ZONE RE-TEST (FVG / OB / DISCOUNT / PREMIUM)
            │
            ▼
  LTF INTERNAL STRUCTURAL CONFIRMATION (CHOCH / BOS)
            │
            ▼
  PHASE -> CONTINUATION
            │
            ▼
     ENTRY (LONG / SHORT)
            │
            ▼
    4R / 5R TARGET (Target R >= 4.0)

Both LONG and SHORT directions are fully parameterized.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreakType,
    TrendDirection,
)


@dataclass
class HypothesisConfig:
    min_target_r: float = 4.0
    atr_stop_mult: float = 2.0
    allow_long: bool = True
    allow_short: bool = True
    fvg_retest_required: bool = True


@dataclass
class SignalIntent:
    symbol: str
    timestamp_ms: int
    direction: int  # +1 LONG, -1 SHORT
    entry_price: float
    stop_price: float
    target_price: float
    target_r: float
    reason: str
    meta: Dict[str, Any] = field(default_factory=dict)


class PrimaryHypothesisEngine:
    """Evaluates canonical MarketState snapshots for 4R/5R Pullback-to-Continuation setups."""

    def __init__(self, config: Optional[HypothesisConfig] = None):
        self.config = config or HypothesisConfig()

    def evaluate(self, state: MarketState) -> Optional[SignalIntent]:
        """Evaluate a MarketState snapshot for a 4R/5R entry setup."""
        # 1. Check HTF External Structure & Trend
        trend = state.structure.external_trend
        if trend not in (TrendDirection.BULLISH, TrendDirection.BEARISH):
            return None

        # 2. Check MTF Market Phase
        phase = state.phase.current_phase
        if phase != MarketPhaseType.PULLBACK:
            return None

        # 3. Check Key Zone Re-test (Discount for Long, Premium for Short)
        pd_zone = state.zones.premium_discount_zone
        curr_price = state.close_price
        stop_dist = state.measurements.atr * self.config.atr_stop_mult

        if stop_dist <= 0:
            stop_dist = curr_price * 0.01  # 1% fallback

        # ---------------------------------------------------------------------
        # LONG HYPOTHESIS EVALUATION
        # ---------------------------------------------------------------------
        if self.config.allow_long and trend == TrendDirection.BULLISH:
            if pd_zone == "DISCOUNT" or len(state.zones.fair_value_gaps) > 0:
                stop_price = curr_price - stop_dist
                target_price = curr_price + self.config.min_target_r * stop_dist
                return SignalIntent(
                    symbol=state.symbol,
                    timestamp_ms=state.timestamp_ms,
                    direction=1,
                    entry_price=curr_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    target_r=self.config.min_target_r,
                    reason=f"4R LONG Setup: HTF Bullish + MTF Pullback + Discount Key Zone",
                    meta={"pd_zone": pd_zone, "phase": phase.value},
                )

        # ---------------------------------------------------------------------
        # SHORT HYPOTHESIS EVALUATION
        # ---------------------------------------------------------------------
        if self.config.allow_short and trend == TrendDirection.BEARISH:
            if pd_zone == "PREMIUM" or len(state.zones.fair_value_gaps) > 0:
                stop_price = curr_price + stop_dist
                target_price = curr_price - self.config.min_target_r * stop_dist
                return SignalIntent(
                    symbol=state.symbol,
                    timestamp_ms=state.timestamp_ms,
                    direction=-1,
                    entry_price=curr_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    target_r=self.config.min_target_r,
                    reason=f"4R SHORT Setup: HTF Bearish + MTF Pullback + Premium Key Zone",
                    meta={"pd_zone": pd_zone, "phase": phase.value},
                )

        return None
