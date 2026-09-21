"""
Product 01: Crypto Platform - MTF Setup & Alignment Engine (V2.1)
Verifies MTF trend alignment with HTF Bias and locates active MTF KeyZones in Premium/Discount.
"""

from dataclasses import dataclass
from typing import Optional
from market_intelligence.primitives import MarketStatePayload, KeyZone, TrendDirection


@dataclass
class MTFSetupResult:
    is_aligned: bool
    strategy_type: str
    active_mtf_keyzone: Optional[KeyZone]
    reason: str = ""


class MTFSetupEngine:

    @staticmethod
    def evaluate_setup(
        htf_bias: TrendDirection,
        mtf_state: MarketStatePayload
    ) -> MTFSetupResult:
        """Verifies MTF trend alignment and locates active MTF KeyZones."""
        mtf_trend = mtf_state.structure_state.external_trend or mtf_state.trend_state.direction or mtf_state.trend

        if mtf_trend in (TrendDirection.NEUTRAL, TrendDirection.RANGING):
            mtf_trend = htf_bias

        if mtf_trend != htf_bias:
            return MTFSetupResult(
                is_aligned=False,
                strategy_type="NONE",
                active_mtf_keyzone=None,
                reason=f"MTF trend ({mtf_trend.value}) is not aligned with HTF bias ({htf_bias.value})."
            )

        matching_zones = [
            z for z in mtf_state.active_keyzones
            if z.direction == htf_bias and not z.is_mitigated
        ]

        selected_zone = matching_zones[-1] if matching_zones else None

        return MTFSetupResult(
            is_aligned=True,
            strategy_type="CONTINUATION_RIDING",
            active_mtf_keyzone=selected_zone,
            reason="MTF setup aligned with HTF Bias."
        )