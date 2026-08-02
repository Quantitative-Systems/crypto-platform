"""
Product 01: Crypto Platform - MTF Setup Engine
Implements Part D of strategy_specification.md v1.1.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, KeyZone, MarketPhase
from strategy.htf_bias import HTFBiasResult


@dataclass
class MTFSetupResult:
    is_aligned: bool
    strategy_type: str  # "PULLBACK_RIDING" or "CONTINUATION_RIDING"
    active_mtf_keyzone: Optional[KeyZone]
    rejection_reason: str = ""


class MTFSetupEngine:

    @staticmethod
    def process_setup(mtf_state: MarketStatePayload, htf_result: HTFBiasResult) -> MTFSetupResult:
        """Confirms MTF structural alignment and identifies MTF Keyzone cushion."""
        if not htf_result.is_valid:
            return MTFSetupResult(
                is_aligned=False, strategy_type="NONE", active_mtf_keyzone=None,
                rejection_reason="HTF Bias is invalid."
            )

        strategy_type = "PULLBACK_RIDING" if htf_result.expected_phase == MarketPhase.PULLBACK else "CONTINUATION_RIDING"

        # Rule 1: MTF trend direction must align with HTF Bias
        if mtf_state.trend != htf_result.bias:
            return MTFSetupResult(
                is_aligned=False, strategy_type=strategy_type, active_mtf_keyzone=None,
                rejection_reason=f"MTF trend ({mtf_state.trend.value}) opposes HTF bias ({htf_result.bias.value})."
            )

        # Rule 2: MTF must have printed a structural event (CHOCH or BOS) in direction of HTF Bias
        if not mtf_state.last_event or mtf_state.last_event.direction != htf_result.bias:
            return MTFSetupResult(
                is_aligned=False, strategy_type=strategy_type, active_mtf_keyzone=None,
                rejection_reason="MTF has not confirmed structural realignment (CHOCH/BOS) with HTF bias."
            )

        # Rule 3: Locate unmitigated MTF Keyzone (OB or FVG) in direction of HTF Bias
        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_result.bias and not z.is_mitigated
        ]

        if not matching_zones:
            return MTFSetupResult(
                is_aligned=False, strategy_type=strategy_type, active_mtf_keyzone=None,
                rejection_reason="No unmitigated MTF Keyzones available."
            )

        return MTFSetupResult(
            is_aligned=True,
            strategy_type=strategy_type,
            active_mtf_keyzone=matching_zones[-1],
            rejection_reason=""
        )