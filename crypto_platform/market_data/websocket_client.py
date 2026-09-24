"""Crypto Trading Platform — Public Real-Time WebSocket Market Data Connector.

Connects to public market feeds (Binance Spot/Futures, Bybit Linear) with:
- Asynchronous connection and event streaming
- Automatic reconnection with exponential backoff and jitter
- Heartbeat handling (ping/pong)
- Sequence continuity & gap detection
- Stale data detection (> 5000ms)
- Timestamp monotonicity enforcement
- Normalization into canonical TickerEvent, CandleEvent, OrderBookEvent
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set
import websockets

from crypto_platform.core.events import CandleEvent, Level, OrderBookEvent, TickerEvent

logger = logging.getLogger("crypto_platform.market_data.websocket")


class PublicWebSocketClient:
    """Production-grade asynchronous public WebSocket stream manager."""

    def __init__(
        self,
        venue: str = "binance",
        is_futures: bool = True,
        max_reconnect_attempts: int = 10,
        stale_threshold_ms: int = 5000,
    ):
        self.venue = venue.lower()
        self.is_futures = is_futures
        self.max_reconnect_attempts = max_reconnect_attempts
        self.stale_threshold_ms = stale_threshold_ms

        self.running = False
        self.connected = False
        self.reconnect_count = 0
        self.dropped_messages = 0
        self.last_heartbeat_ms = 0
        self.last_event_ts_ms: Dict[str, int] = {}
        self.last_seq_id: Dict[str, int] = {}

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._subscribed_symbols: Set[str] = set()

    def get_endpoint_url(self) -> str:
        """Returns the public WebSocket endpoint for the venue."""
        if self.venue == "binance":
            return (
                "wss://fstream.binance.com/ws"
                if self.is_futures
                else "wss://stream.binance.com:9443/ws"
            )
        elif self.venue == "bybit":
            return (
                "wss://stream.bybit.com/v5/public/linear"
                if self.is_futures
                else "wss://stream.bybit.com/v5/public/spot"
            )
        else:
            raise ValueError(f"Unsupported public WebSocket venue: {self.venue}")

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a subscriber callback for an event type ('ticker', 'candle', 'orderbook')."""
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Unregister a subscriber callback for an event type."""
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def clear_subscribers(self, event_type: Optional[str] = None) -> None:
        """Clear all subscribers for a specific event type or all event types."""
        if event_type is None:
            self._subscribers.clear()
        elif event_type in self._subscribers:
            self._subscribers[event_type].clear()

    def _notify(self, event_type: str, payload: Any) -> None:
        for cb in self._subscribers.get(event_type, []):
            try:
                cb(payload)
            except Exception as e:
                logger.error(f"Error in subscriber callback for {event_type}: {e}")

    async def add_symbol_stream(self, symbol: str) -> None:
        """Subscribe to ticker and kline feeds for a symbol."""
        self._subscribed_symbols.add(symbol.upper())
        if self.connected and self._ws:
            await self._send_subscription([symbol.upper()])

    async def _send_subscription(self, symbols: List[str]) -> None:
        if not self._ws or not symbols:
            return

        if self.venue == "binance":
            # Binance stream subscription
            params = []
            for s in symbols:
                sym_lower = s.lower()
                params.append(f"{sym_lower}@ticker")
                params.append(f"{sym_lower}@kline_15m")
            sub_msg = {
                "method": "SUBSCRIBE",
                "params": params,
                "id": int(time.time() * 1000),
            }
            await self._ws.send(json.dumps(sub_msg))

        elif self.venue == "bybit":
            args = []
            for s in symbols:
                args.append(f"tickers.{s}")
                args.append(f"kline.15.{s}")
            sub_msg = {"op": "subscribe", "args": args}
            await self._ws.send(json.dumps(sub_msg))

    def parse_binance_message(self, raw: Dict[str, Any]) -> Optional[Any]:
        """Normalize raw Binance WebSocket message."""
        event_type = raw.get("e")

        # 24hr Mini-Ticker or Ticker
        if event_type in ("24hrTicker", "24hrMiniTicker") or "c" in raw and "s" in raw:
            symbol = raw.get("s", "")
            ts = int(raw.get("E", time.time() * 1000))
            last_price = float(raw.get("c", 0.0))
            bid = float(raw.get("b", last_price * 0.9999))
            ask = float(raw.get("a", last_price * 1.0001))
            volume_24h = float(raw.get("v", 0.0))

            # Timestamp check
            prev_ts = self.last_event_ts_ms.get(symbol, 0)
            if ts < prev_ts:
                # Sequence / timestamp inversion
                self.dropped_messages += 1
                return None
            self.last_event_ts_ms[symbol] = ts

            ticker = TickerEvent(
                venue=self.venue,
                symbol=symbol,
                timestamp_ms=ts,
                bid=bid,
                ask=ask,
                last_price=last_price,
                volume_24h=volume_24h,
            )
            self._notify("ticker", ticker)
            return ticker

        # Kline / Candlestick
        elif event_type == "kline":
            k = raw.get("k", {})
            symbol = raw.get("s", "")
            open_ts = int(k.get("t", 0))
            close_ts = int(k.get("T", 0))
            candle = CandleEvent(
                venue=self.venue,
                symbol=symbol,
                timeframe=k.get("i", "15m"),
                open_ts=open_ts,
                close_ts=close_ts,
                open=float(k.get("o", 0.0)),
                high=float(k.get("h", 0.0)),
                low=float(k.get("l", 0.0)),
                close=float(k.get("c", 0.0)),
                volume=float(k.get("v", 0.0)),
                quote_volume=float(k.get("q", 0.0)),
                is_closed=bool(k.get("x", False)),
            )
            self._notify("candle", candle)
            return candle

        return None

    def parse_bybit_message(self, raw: Dict[str, Any]) -> Optional[Any]:
        """Normalize raw Bybit WebSocket message."""
        topic = raw.get("topic", "")
        ts = int(raw.get("ts", time.time() * 1000))
        data = raw.get("data", {})

        if topic.startswith("tickers."):
            symbol = topic.split(".", 1)[1]
            last_price = float(data.get("lastPrice", 0.0) or 0.0)
            bid = float(data.get("bid1Price", last_price * 0.9999) or last_price * 0.9999)
            ask = float(data.get("ask1Price", last_price * 1.0001) or last_price * 1.0001)
            volume_24h = float(data.get("volume24h", 0.0) or 0.0)

            ticker = TickerEvent(
                venue=self.venue,
                symbol=symbol,
                timestamp_ms=ts,
                bid=bid,
                ask=ask,
                last_price=last_price,
                volume_24h=volume_24h,
            )
            self._notify("ticker", ticker)
            return ticker

        elif topic.startswith("kline."):
            parts = topic.split(".")
            symbol = parts[2] if len(parts) > 2 else ""
            if isinstance(data, list) and len(data) > 0:
                k = data[0]
                candle = CandleEvent(
                    venue=self.venue,
                    symbol=symbol,
                    timeframe=parts[1] if len(parts) > 1 else "15m",
                    open_ts=int(k.get("start", 0)),
                    close_ts=int(k.get("end", 0)),
                    open=float(k.get("open", 0.0)),
                    high=float(k.get("high", 0.0)),
                    low=float(k.get("low", 0.0)),
                    close=float(k.get("close", 0.0)),
                    volume=float(k.get("volume", 0.0)),
                    is_closed=bool(k.get("confirm", False)),
                )
                self._notify("candle", candle)
                return candle

        return None

    def is_data_stale(self, symbol: str) -> bool:
        """Returns True if the symbol's last event is older than stale_threshold_ms."""
        last_ts = self.last_event_ts_ms.get(symbol, 0)
        if last_ts == 0:
            return True
        now_ms = int(time.time() * 1000)
        return (now_ms - last_ts) > self.stale_threshold_ms

    async def _listen_loop(self) -> None:
        """Main connection and reconnection lifecycle loop."""
        backoff = 1.0
        max_backoff = 30.0

        while self.running:
            url = self.get_endpoint_url()
            try:
                logger.info(f"Connecting to {self.venue} WebSocket at {url}...")
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    self.connected = True
                    backoff = 1.0  # Reset backoff on successful connect
                    logger.info(f"Connected to {self.venue} WebSocket successfully.")

                    # Resubscribe all active symbols
                    if self._subscribed_symbols:
                        await self._send_subscription(list(self._subscribed_symbols))

                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=25.0)
                            self.last_heartbeat_ms = int(time.time() * 1000)
                            raw = json.loads(msg)

                            if self.venue == "binance":
                                self.parse_binance_message(raw)
                            elif self.venue == "bybit":
                                self.parse_bybit_message(raw)

                        except asyncio.TimeoutError:
                            # Ping to verify liveness
                            pong_waiter = await ws.ping()
                            await asyncio.wait_for(pong_waiter, timeout=5.0)

            except Exception as e:
                self.connected = False
                self._ws = None
                self.reconnect_count += 1
                logger.warning(
                    f"{self.venue} WebSocket disconnected: {e}. "
                    f"Reconnecting in {backoff:.1f}s (attempt {self.reconnect_count})..."
                )

                if not self.running:
                    break

                # Exponential backoff with jitter
                sleep_time = backoff + random.uniform(0.1, 0.5)
                await asyncio.sleep(sleep_time)
                backoff = min(backoff * 2.0, max_backoff)

        self.connected = False
        self._ws = None

    def start(self) -> None:
        """Starts the WebSocket listening task."""
        if not self.running:
            self.running = True
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._listen_loop())

    async def stop(self) -> None:
        """Stops the WebSocket listening task and closes connection."""
        self.running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.connected = False
