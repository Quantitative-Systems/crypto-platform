"""Crypto Trading Platform — canonical event schemas.

All venue-specific payloads normalize into these immutable event structures
to isolate venue changes and enable event-sourced audit and replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass(frozen=True)
class CandleEvent:
    venue: str
    symbol: str
    timeframe: str
    open_ts: int
    close_ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    is_closed: bool = True


@dataclass(frozen=True)
class Level:
    price: float
    quantity: float


@dataclass(frozen=True)
class OrderBookEvent:
    venue: str
    symbol: str
    timestamp_ms: int
    bids: List[Level]
    asks: List[Level]


@dataclass(frozen=True)
class TickerEvent:
    venue: str
    symbol: str
    timestamp_ms: int
    bid: float
    ask: float
    last_price: float
    volume_24h: float = 0.0


@dataclass(frozen=True)
class FundingRateEvent:
    venue: str
    symbol: str
    timestamp_ms: int
    funding_rate: float
    mark_price: float
    index_price: float
    next_funding_time_ms: int


@dataclass(frozen=True)
class SignalEvent:
    strategy_id: str
    symbol: str
    direction: int          # +1 long, -1 short
    confidence: float
    timestamp_ms: int
    horizon: str
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationEvent:
    account_id: str
    venue: str
    timestamp_ms: int
    in_sync: bool
    discrepancies: List[str] = field(default_factory=list)
    action_taken: str = "NONE"


@dataclass(frozen=True)
class SystemAlertEvent:
    level: str              # INFO, WARNING, CRITICAL, EMERGENCY
    source: str
    message: str
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    context: Dict[str, Any] = field(default_factory=dict)
