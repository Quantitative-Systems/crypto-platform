"""Liquidity Profiles and Market Depth Specifications.

Tracks microstructure liquidity parameters for admitted instruments:
- Typical spread in basis points (bps)
- 24-hour volume in USD
- Top of book depth ($ at 10 bps and 50 bps)
- Trading session calendar (true 24/7 vs weekend-closed commodities/forex quotes)
- Maximum allowed execution slippage
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TradingSessionType(str, Enum):
    """Trading session operating schedule."""
    CONTINUOUS_24_7 = "CONTINUOUS_24_7"             # Native crypto (BTC/USDT, ETH/USD) trades 24/7/365
    WEEKDAY_24_5 = "WEEKDAY_24_5"                   # Fiat / Forex quotes (EUR, GBP, JPY) close on weekends
    COMMODITY_HOURS = "COMMODITY_HOURS"             # Gold (XAU) futures / spot breaks and weekend closure


@dataclass(frozen=True)
class LiquidityProfile:
    """Microstructure liquidity and availability profile."""
    typical_spread_bps: float = 3.0          # e.g. 3 bps = 0.03%
    max_tolerated_spread_bps: float = 15.0   # Beyond this, market is deemed illiquid / frozen
    daily_volume_usd: float = 50_000_000.0   # Rolling 24h turnover in USD
    min_required_volume_usd: float = 1_000_000.0  # Admission minimum
    bid_depth_10bps_usd: float = 500_000.0   # Capital available within 10 bps of mid
    ask_depth_10bps_usd: float = 500_000.0
    session_type: TradingSessionType = TradingSessionType.CONTINUOUS_24_7
    expected_slippage_bps: float = 2.0

    def is_currently_liquid(self, observed_spread_bps: float) -> tuple[bool, str]:
        """Check if current market conditions meet liquidity standards."""
        if observed_spread_bps > self.max_tolerated_spread_bps:
            return False, f"Observed spread {observed_spread_bps:.1f} bps exceeds limit {self.max_tolerated_spread_bps:.1f} bps"
        if self.daily_volume_usd < self.min_required_volume_usd:
            return False, f"Daily volume ${self.daily_volume_usd:,.0f} below requirement ${self.min_required_volume_usd:,.0f}"
        return True, "LIQUID"

    def is_market_open_at(self, day_of_week: int, hour_utc: int) -> bool:
        """Check if trading session is active (Monday=0 ... Sunday=6)."""
        if self.session_type == TradingSessionType.CONTINUOUS_24_7:
            return True
        # For WEEKDAY_24_5: Closed from Friday 22:00 UTC to Sunday 22:00 UTC
        if self.session_type == TradingSessionType.WEEKDAY_24_5:
            if day_of_week == 5:  # Saturday
                return False
            if day_of_week == 4 and hour_utc >= 22:  # Friday late
                return False
            if day_of_week == 6 and hour_utc < 22:   # Sunday before open
                return False
            return True
        # Commodity hours typically close weekends and daily maintenance break (21:00-22:00 UTC)
        if self.session_type == TradingSessionType.COMMODITY_HOURS:
            if day_of_week == 5:
                return False
            if day_of_week == 4 and hour_utc >= 21:
                return False
            if day_of_week == 6 and hour_utc < 22:
                return False
            if hour_utc == 21:  # Daily maintenance settlement break
                return False
            return True
        return True
