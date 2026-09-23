"""
Crypto Trading Platform — Realtime Market Data Stream Manager.

Orchestrates:
- WebSocket message ingestion with REST fallback polling
- Monotonic sequence ID validation
- Timestamp continuity & gap detection
- In-flight deduplication
- Normalization into exchange-neutral market data schemas
- Local storage persistence
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from market_data.schemas.market_data_schemas import OHLCVRecord, TradeRecord, OrderBookL2Record
from market_data.errors import DataCorruptionError, MarketDataError


@dataclass
class StreamHealth:
    symbol: str
    venue: str
    connected: bool = False
    messages_received: int = 0
    gaps_detected: int = 0
    duplicate_count: int = 0
    last_sequence_id: int = 0
    last_timestamp_ms: int = 0
    reconnection_count: int = 0


class RealtimeStreamManager:
    """
    Robust realtime market data feed processor.
    """

    def __init__(self, venue: str = "BINANCE"):
        self.venue = venue
        self._health: Dict[str, StreamHealth] = {}
        self._seen_trade_ids: Set[str] = set()
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def get_health(self, symbol: str) -> StreamHealth:
        if symbol not in self._health:
            self._health[symbol] = StreamHealth(symbol=symbol, venue=self.venue)
        return self._health[symbol]

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def _notify(self, event_type: str, payload: Any) -> None:
        for cb in self._subscribers.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass

    def process_raw_kline(self, symbol: str, raw: Dict[str, Any], is_closed: bool = True) -> Optional[OHLCVRecord]:
        health = self.get_health(symbol)
        health.messages_received += 1

        ts = int(raw.get("t", raw.get("timestamp", 0)))
        if ts <= 0:
            raise DataCorruptionError(f"Invalid timestamp in kline: {raw}")

        # Timestamp monotonicity check
        if health.last_timestamp_ms > 0 and ts < health.last_timestamp_ms:
            raise DataCorruptionError(f"Timestamp inversion on {symbol}: {ts} < {health.last_timestamp_ms}")

        # Gap check for 15m (900s = 900,000ms)
        tf_ms = 900_000
        if health.last_timestamp_ms > 0 and ts - health.last_timestamp_ms > tf_ms * 1.5:
            health.gaps_detected += 1

        health.last_timestamp_ms = ts

        record = OHLCVRecord(
            timestamp=ts // 1000 if ts > 10_000_000_000 else ts,
            open=float(raw.get("o", raw.get("open", 0.0))),
            high=float(raw.get("h", raw.get("high", 0.0))),
            low=float(raw.get("l", raw.get("low", 0.0))),
            close=float(raw.get("c", raw.get("close", 0.0))),
            volume=float(raw.get("v", raw.get("volume", 0.0))),
            symbol=symbol,
            venue=self.venue,
        )

        if is_closed:
            self._notify("kline_closed", record)
        return record

    def process_raw_trade(self, symbol: str, raw: Dict[str, Any]) -> Optional[TradeRecord]:
        health = self.get_health(symbol)
        health.messages_received += 1

        tid = str(raw.get("t", raw.get("trade_id", "")))
        if tid in self._seen_trade_ids:
            health.duplicate_count += 1
            return None  # Deduplicate in-flight

        self._seen_trade_ids.add(tid)
        if len(self._seen_trade_ids) > 100_000:
            # maintain bounded buffer
            self._seen_trade_ids.clear()

        record = TradeRecord(
            trade_id=tid,
            timestamp_ms=int(raw.get("T", raw.get("timestamp_ms", int(time.time() * 1000)))),
            symbol=symbol,
            price=float(raw.get("p", raw.get("price", 0.0))),
            quantity=float(raw.get("q", raw.get("quantity", 0.0))),
            side="BUY" if raw.get("m", False) is False else "SELL",
            is_liquidation=bool(raw.get("is_liquidation", False)),
            venue=self.venue,
        )
        self._notify("trade", record)
        return record

    def process_raw_order_book(self, symbol: str, raw: Dict[str, Any]) -> OrderBookL2Record:
        health = self.get_health(symbol)
        health.messages_received += 1

        seq_id = int(raw.get("lastUpdateId", raw.get("sequence_id", 0)))
        if health.last_sequence_id > 0 and seq_id < health.last_sequence_id:
            raise DataCorruptionError(f"Sequence regression in book {symbol}: {seq_id} < {health.last_sequence_id}")
        health.last_sequence_id = seq_id

        bids = [(float(p), float(q)) for p, q in raw.get("bids", [])]
        asks = [(float(p), float(q)) for p, q in raw.get("asks", [])]

        record = OrderBookL2Record(
            timestamp_ms=int(raw.get("E", int(time.time() * 1000))),
            sequence_id=seq_id,
            symbol=symbol,
            bids=bids,
            asks=asks,
            venue=self.venue,
        )
        self._notify("order_book", record)
        return record
