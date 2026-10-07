"""Causal Event Contracts & Data Structures.

Defines the formal contracts for:
1. Macro, Monetary, Cross-Market, Crypto-Native, and Regulatory Events.
2. Expectation vs. Actual Surprise Model (Actual - Expected, Revision, Magnitude).
3. Event Clock Temporal Context (T-24h to T+24h).
4. Causal Transmission Chains (Event -> Transmission -> Affected Assets -> Expected Response).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EventCategory(str, Enum):
    MACROECONOMIC = "MACROECONOMIC"        # CPI, PCE, NFP, GDP, PMI, Retail Sales
    MONETARY_POLICY = "MONETARY_POLICY"    # Fed, ECB, BOJ rate decisions, balance sheet
    CROSS_MARKET = "CROSS_MARKET"          # DXY surge, UST yield spike, VIX spike, commodities
    CRYPTO_NATIVE = "CRYPTO_NATIVE"        # ETF flows, stablecoin supply, liquidation cascade, funding extreme
    FUNDAMENTAL = "FUNDAMENTAL"            # Earnings, protocol revenue, token unlocks
    REGULATORY_GEOPOLITICAL = "REGULATORY_GEOPOLITICAL" # SEC action, sanctions, wars, ETF approval


class EventImportance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"                  # FOMC, CPI, NFP, ETF Approval/Ban, Systemic Depeg


class SurpriseDirection(str, Enum):
    UPSIDE = "UPSIDE"
    DOWNSIDE = "DOWNSIDE"
    IN_LINE = "IN_LINE"


class EventClockPhase(str, Enum):
    """Temporal proximity relative to a scheduled market-moving catalyst."""
    FAR_PRE_EVENT = "FAR_PRE_EVENT"        # > T-24h
    T_MINUS_24H = "T_MINUS_24H"            # T-24h to T-4h (position de-risking)
    T_MINUS_4H = "T_MINUS_4H"              # T-4h to T-1h (liquidity withdrawal)
    T_MINUS_1H = "T_MINUS_1H"              # T-1h to T-15m (compression & spread widening)
    T_MINUS_15M = "T_MINUS_15M"            # T-15m to Catalyst (pre-event freeze)
    AT_EVENT = "AT_EVENT"                  # Catalyst release to T+15m (volatility expansion, sweep, displacement)
    T_PLUS_15M = "T_PLUS_15M"              # T+15m to T+1h (initial price discovery)
    T_PLUS_1H = "T_PLUS_1H"                # T+1h to T+4h (trend continuation or mean reversion)
    T_PLUS_4H = "T_PLUS_4H"                # T+4h to T+24h (new structural equilibrium)
    POST_EQUILIBRIUM = "POST_EQUILIBRIUM"  # > T+24h


@dataclass
class EventSurprise:
    """Quantitative expectation-vs-actual measurement."""
    actual: float
    expected: Optional[float] = None
    previous: Optional[float] = None
    revision: Optional[float] = None
    unit: str = "%"
    
    @property
    def raw_surprise(self) -> Optional[float]:
        """Actual - Expected."""
        if self.expected is not None:
            return self.actual - self.expected
        return None

    @property
    def period_change(self) -> Optional[float]:
        """Actual - Previous."""
        if self.previous is not None:
            return self.actual - self.previous
        return None

    @property
    def direction(self) -> SurpriseDirection:
        if self.raw_surprise is None or abs(self.raw_surprise) < 1e-6:
            return SurpriseDirection.IN_LINE
        return SurpriseDirection.UPSIDE if self.raw_surprise > 0 else SurpriseDirection.DOWNSIDE

    @property
    def standardized_surprise(self) -> float:
        """Surprise normalized by standard dev or expected scale if available."""
        if self.raw_surprise is None:
            return 0.0
        # If absolute expected is non-zero, calculate percentage divergence
        if self.expected is not None and abs(self.expected) > 1e-4:
            return self.raw_surprise / abs(self.expected)
        return self.raw_surprise


@dataclass
class TransmissionChain:
    """Hypothesized or empirical transmission chain from event to asset classes."""
    primary_channel: str                   # e.g., "Interest Rate Expectations"
    secondary_channel: str                 # e.g., "US Dollar & Yields"
    tertiary_channel: str                  # e.g., "Global Risk Appetite & Crypto Liquidity"
    affected_assets: List[str]             # e.g., ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    expected_market_response: str          # e.g., "Liquidity flush followed by trend continuation"
    historical_hit_rate: float = 0.50      # Empirically measured validation


@dataclass
class CausalEvent:
    """Immutable, timestamped market event descriptor."""
    event_id: str
    event_name: str
    category: EventCategory
    importance: EventImportance
    timestamp_ms: int                      # Exact public release timestamp (strictly causal: t_release <= t_bar)
    surprise: EventSurprise
    affected_assets: List[str] = field(default_factory=list)
    transmission: Optional[TransmissionChain] = None
    headline: str = ""
    source: str = "OFFICIAL"
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "category": self.category.value,
            "importance": self.importance.value,
            "timestamp_ms": self.timestamp_ms,
            "surprise": {
                "actual": self.surprise.actual,
                "expected": self.surprise.expected,
                "previous": self.surprise.previous,
                "revision": self.surprise.revision,
                "raw_surprise": self.surprise.raw_surprise,
                "direction": self.surprise.direction.value,
                "standardized_surprise": self.surprise.standardized_surprise,
            },
            "affected_assets": self.affected_assets,
            "headline": self.headline,
            "source": self.source,
            "meta": self.meta,
        }


@dataclass
class EventTimeContext:
    """Temporal proximity state relative to upcoming and past events."""
    current_time_ms: int
    clock_phase: EventClockPhase
    nearest_upcoming_event: Optional[CausalEvent] = None
    time_to_upcoming_ms: Optional[int] = None
    nearest_past_event: Optional[CausalEvent] = None
    time_since_past_ms: Optional[int] = None
    is_trading_prohibited: bool = False
    is_compression_expected: bool = False
    is_volatility_expansion_expected: bool = False
    reason: str = "Normal market conditions"
