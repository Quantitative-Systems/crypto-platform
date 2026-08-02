"""
Product 01: Crypto Platform - Strategy A: Pullback Riding Engine
Implements Strategy A rules strictly according to strategy_specification.md v1.1.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, TrendDirection, KeyZone, MarketPhase, EventType


@dataclass
class StrategyAResult:
    is_valid_setup: bool
    mtf_keyzone: Optional[KeyZone]
    reason: str


class StrategyAPullbackEngine:

    @staticmethod
    def evaluate_pullback_setup(
        htf_state: MarketStatePayload,
        mtf_state: MarketStatePayload
    ) -> StrategyAResult:
        """
        Strategy A Rules:
        1. HTF Phase must be PULLBACK (HTF recently printed a BOS).
        2. MTF trend must have completed its structural shift (CHOCH/BOS) back into HTF Bias alignment.
        3. Active unmitigated MTF Keyzone must be present.
        """
        if htf_state.trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF trend is not trending.")

        # Rule 1: HTF must be in PULLBACK phase
        if not htf_state.last_event or htf_state.last_event.event_type != EventType.BOS:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="HTF is not in PULLBACK phase (No recent BOS).")

        # Rule 2: MTF Trend must align with HTF Bias after retracement
        if mtf_state.trend != htf_state.trend:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason=f"MTF trend ({mtf_state.trend.value}) has not realigned with HTF bias ({htf_state.trend.value}).")

        # Rule 3: MTF must have printed a CHOCH/BOS confirming realignment
        if not mtf_state.last_event or mtf_state.last_event.direction != htf_state.trend:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="MTF structural realignment CHOCH/BOS missing.")

        # Rule 4: Active unmitigated MTF Keyzone
        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_state.trend and not z.is_mitigated
        ]

        if not matching_zones:
            return StrategyAResult(is_valid_setup=False, mtf_keyzone=None, reason="No unmitigated MTF Keyzone found for Pullback entry.")

        return StrategyAResult(
            is_valid_setup=True,
            mtf_keyzone=matching_zones[-1],
            reason="Strategy A (Pullback Riding) Setup Verified."
        )