"""
Quantitative Crypto Platform (QCP) — Exchange-Neutral Market Data Schemas.

Defines canonical dataclass models for the 10 core market data streams:
1. OHLCVRecord
2. TradeRecord
3. FundingRateRecord
4. OpenInterestRecord
5. LiquidationRecord
6. OrderBookL2Record
7. MarkPriceRecord
8. IndexPriceRecord
9. FeeScheduleRecord
10. VenueMetadataRecord
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OHLCVRecord:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = "SOL/USDT"
    timeframe: str = "4h"
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TradeRecord:
    trade_id: str
    timestamp_ms: int
    symbol: str
    price: float
    quantity: float
    side: str  # BUY or SELL
    is_liquidation: bool = False
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FundingRateRecord:
    timestamp: int
    symbol: str
    rate: float
    next_funding_time: int
    annualized_rate_pct: float
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpenInterestRecord:
    timestamp: int
    symbol: str
    open_interest_units: float
    open_interest_usd: float
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiquidationRecord:
    liquidation_id: str
    timestamp_ms: int
    symbol: str
    side: str  # BUY (short liquidated) or SELL (long liquidated)
    price: float
    quantity: float
    notional_usd: float
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrderBookL2Record:
    timestamp_ms: int
    sequence_id: int
    symbol: str
    bids: List[Tuple[float, float]]  # [(price, qty), ...]
    asks: List[Tuple[float, float]]  # [(price, qty), ...]
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarkPriceRecord:
    timestamp_ms: int
    symbol: str
    mark_price: float
    index_price: float
    funding_rate: float
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndexPriceRecord:
    timestamp_ms: int
    symbol: str
    index_price: float
    constituent_exchanges: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FeeScheduleRecord:
    venue: str
    tier_name: str
    maker_fee_bps: float
    taker_fee_bps: float
    effective_from_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VenueMetadataRecord:
    venue_id: str
    name: str
    symbols_supported: List[str]
    tick_sizes: Dict[str, float]
    lot_sizes: Dict[str, float]
    min_notionals_usd: Dict[str, float]
    status: str = "ACTIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
