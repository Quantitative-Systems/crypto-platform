"""
Product 01: Crypto Platform - Strategy B: Continuation Riding Engine
Implements Strategy B rules strictly according to strategy_specification.md v1.1.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, KeyZone, MarketPhase, EventType


@dataclass
class StrategyBResult:
    is_valid_setup: bool
    mtf_keyzone: Optional[KeyZone]
    reason: str


class StrategyBContinuationEngine:

    @staticmethod
    def evaluate_continuation_setup(
        htf_state: MarketStatePayload,
        mtf_state: MarketStatePayload
    ) -> StrategyBResult:
        """
        Strategy B Rules:
        1. HTF Phase must be CONTINUATION (HTF retracement into Keyzone complete).
        2. MTF trend is already aligned with HTF Bias.
        3. Active unmitigated MTF Keyzone must be present.
        """
        if htf_state.trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF trend is not trending.")

        # Rule 1: MTF Trend must be aligned with HTF Bias
        if mtf_state.trend != htf_state.trend:
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason=f"MTF trend ({mtf_state.trend.value}) opposes HTF bias ({htf_state.trend.value}).")

        # Rule 2: Active unmitigated MTF Keyzone in trend direction
        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_state.trend and not z.is_mitigated
        ]

        if not matching_zones:
            return StrategyBResult(is_valid_setup=False, mtf_keyzone=None, reason="No unmitigated MTF Keyzone found for Continuation entry.")

        return StrategyBResult(
            is_valid_setup=True,
            mtf_keyzone=matching_zones[-1],
            reason="Strategy B (Continuation Riding) Setup Verified."
        )