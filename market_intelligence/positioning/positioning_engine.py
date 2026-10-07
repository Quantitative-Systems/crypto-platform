"""Positioning Intelligence Engine: Open Interest, Funding, Basis, and Trapped Traders.

Evaluates market positioning extremes to identify where market participants are over-leveraged
and where liquidation cascades or short squeezes create asymmetric technical edges.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class FundingState(str, Enum):
    EXTREME_NEGATIVE = "EXTREME_NEGATIVE"  # Shorts heavily crowded, paying longs > 10 bps
    DISCOUNT = "DISCOUNT"                  # Negative funding, mild short bias
    NEUTRAL = "NEUTRAL"                    # Standard baseline (0.0 to 10.0 bps annualized ~ 10%)
    ELEVATED = "ELEVATED"                  # Longs crowded (15 to 30 bps per 8h)
    EXTREME_POSITIVE = "EXTREME_POSITIVE"  # Extreme long leverage (> 30 bps per 8h, fragile)


class TrappedState(str, Enum):
    NONE = "NONE"
    SHORT_SQUEEZE_PRIME = "SHORT_SQUEEZE_PRIME" # Bullish structure + high OI + negative funding
    LONG_LIQUIDATION_RISK = "LONG_LIQUIDATION_RISK" # Overextended longs + extreme positive funding
    CASCADE_POST_FLUSH = "CASCADE_POST_FLUSH" # Large liquidation volume just swept, books cleared


@dataclass
class PositioningSnapshot:
    """Microstructure and derivative positioning state at timestamp t."""
    timestamp_ms: int
    open_interest_usd: float = 1e9
    oi_change_pct_24h: float = 0.0
    funding_rate_8h_bps: float = 1.0       # Standard ~ 1 bps (0.01% per 8h)
    funding_state: FundingState = FundingState.NEUTRAL
    liquidation_long_usd_24h: float = 0.0
    liquidation_short_usd_24h: float = 0.0
    annualized_basis_pct: float = 5.0      # Spot vs perp basis %
    implied_vol_atm_30d: float = 55.0      # Options IV
    put_call_skew_25d: float = 0.0         # Positive = puts expensive, negative = calls expensive
    long_short_ratio: float = 1.0
    exchange_netflow_usd_24h: float = 0.0  # Positive = net inflow to exchanges (sell pressure)
    trapped_setup: TrappedState = TrappedState.NONE
    edge_alignment_score: float = 1.0      # Sizing/confidence multiplier (0.5 to 1.5)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "open_interest_usd": self.open_interest_usd,
            "oi_change_pct_24h": self.oi_change_pct_24h,
            "funding_rate_8h_bps": self.funding_rate_8h_bps,
            "funding_state": self.funding_state.value,
            "liquidation_long_usd_24h": self.liquidation_long_usd_24h,
            "liquidation_short_usd_24h": self.liquidation_short_usd_24h,
            "annualized_basis_pct": self.annualized_basis_pct,
            "implied_vol_atm_30d": self.implied_vol_atm_30d,
            "put_call_skew_25d": self.put_call_skew_25d,
            "long_short_ratio": self.long_short_ratio,
            "exchange_netflow_usd_24h": self.exchange_netflow_usd_24h,
            "trapped_setup": self.trapped_setup.value,
            "edge_alignment_score": self.edge_alignment_score,
            "meta": self.meta,
        }


class PositioningIntelligenceEngine:
    """Identifies trapped traders, funding crowding, and asymmetric liquidation setups."""

    def __init__(
        self,
        extreme_positive_funding_bps: float = 30.0,
        extreme_negative_funding_bps: float = -10.0,
    ):
        self.extreme_positive_funding_bps = extreme_positive_funding_bps
        self.extreme_negative_funding_bps = extreme_negative_funding_bps

    def evaluate_positioning(
        self,
        timestamp_ms: int,
        positioning_raw: Optional[Dict[str, Any]] = None,
        technical_direction: int = 1, # +1 Bullish, -1 Bearish
    ) -> PositioningSnapshot:
        """Derive positioning snapshot and evaluate edge alignment."""
        raw = positioning_raw or {}

        oi = float(raw.get("open_interest_usd", 2.5e9))
        oi_chg = float(raw.get("oi_change_pct_24h", 0.0))
        funding = float(raw.get("funding_rate_8h_bps", 1.0))
        liq_long = float(raw.get("liquidation_long_usd_24h", 1e7))
        liq_short = float(raw.get("liquidation_short_usd_24h", 1e7))
        basis = float(raw.get("annualized_basis_pct", 5.0))
        iv = float(raw.get("implied_vol_atm_30d", 52.0))
        skew = float(raw.get("put_call_skew_25d", 0.0))
        ls_ratio = float(raw.get("long_short_ratio", 1.05))
        netflow = float(raw.get("exchange_netflow_usd_24h", 0.0))

        # Funding classification
        if funding >= self.extreme_positive_funding_bps:
            f_state = FundingState.EXTREME_POSITIVE
        elif funding > 15.0:
            f_state = FundingState.ELEVATED
        elif funding <= self.extreme_negative_funding_bps:
            f_state = FundingState.EXTREME_NEGATIVE
        elif funding < -2.0:
            f_state = FundingState.DISCOUNT
        else:
            f_state = FundingState.NEUTRAL

        # Trapped Trader Synthesis
        trapped = TrappedState.NONE
        edge_mult = 1.0

        if technical_direction == 1: # Looking for Long
            if f_state == FundingState.EXTREME_NEGATIVE and oi_chg > 5.0:
                # Shorts aggressively fighting a bull trend -> Short Squeeze Prime!
                trapped = TrappedState.SHORT_SQUEEZE_PRIME
                edge_mult = 1.35
            elif f_state == FundingState.EXTREME_POSITIVE:
                # Longs over-leveraged in a bull trend -> fragile, high flush risk
                trapped = TrappedState.LONG_LIQUIDATION_RISK
                edge_mult = 0.65 # Haircut sizing
            elif liq_long > 5e7: # Recent long liquidation flush cleared weak hands
                trapped = TrappedState.CASCADE_POST_FLUSH
                edge_mult = 1.20
        elif technical_direction == -1: # Looking for Short
            if f_state == FundingState.EXTREME_POSITIVE and oi_chg > 5.0:
                # Longs trapped in bear trend -> Long Liquidation Flush Prime!
                trapped = TrappedState.LONG_LIQUIDATION_RISK
                edge_mult = 1.35
            elif f_state == FundingState.EXTREME_NEGATIVE:
                # Shorts already crowded -> fragile to squeeze
                trapped = TrappedState.SHORT_SQUEEZE_PRIME
                edge_mult = 0.65 # Haircut sizing

        return PositioningSnapshot(
            timestamp_ms=timestamp_ms,
            open_interest_usd=oi,
            oi_change_pct_24h=oi_chg,
            funding_rate_8h_bps=funding,
            funding_state=f_state,
            liquidation_long_usd_24h=liq_long,
            liquidation_short_usd_24h=liq_short,
            annualized_basis_pct=basis,
            implied_vol_atm_30d=iv,
            put_call_skew_25d=skew,
            long_short_ratio=ls_ratio,
            exchange_netflow_usd_24h=netflow,
            trapped_setup=trapped,
            edge_alignment_score=edge_mult,
        )
