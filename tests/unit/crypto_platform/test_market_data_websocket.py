"""Unit tests for PublicWebSocketClient message parsing, normalization, and stale detection."""
import time
import pytest
from crypto_platform.market_data.websocket_client import PublicWebSocketClient
from crypto_platform.core.events import CandleEvent, TickerEvent


def test_endpoint_selection():
    client_binance_fut = PublicWebSocketClient(venue="binance", is_futures=True)
    assert client_binance_fut.get_endpoint_url() == "wss://fstream.binance.com/ws"

    client_binance_spot = PublicWebSocketClient(venue="binance", is_futures=False)
    assert client_binance_spot.get_endpoint_url() == "wss://stream.binance.com:9443/ws"

    client_bybit_fut = PublicWebSocketClient(venue="bybit", is_futures=True)
    assert client_bybit_fut.get_endpoint_url() == "wss://stream.bybit.com/v5/public/linear"


def test_binance_ticker_parsing():
    client = PublicWebSocketClient(venue="binance")
    received_tickers = []
    client.subscribe("ticker", lambda t: received_tickers.append(t))

    now_ms = int(time.time() * 1000)
    raw_msg = {
        "e": "24hrTicker",
        "E": now_ms,
        "s": "BTCUSDT",
        "c": "65432.10",
        "b": "65430.00",
        "a": "65435.00",
        "v": "1234.5",
    }
    ticker = client.parse_binance_message(raw_msg)
    assert ticker is not None
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price == 65432.10
    assert ticker.bid == 65430.00
    assert ticker.ask == 65435.00
    assert len(received_tickers) == 1


def test_binance_kline_parsing():
    client = PublicWebSocketClient(venue="binance")
    received_candles = []
    client.subscribe("candle", lambda c: received_candles.append(c))

    raw_msg = {
        "e": "kline",
        "E": 1700000000000,
        "s": "ETHUSDT",
        "k": {
            "t": 1700000000000,
            "T": 1700000900000,
            "s": "ETHUSDT",
            "i": "15m",
            "o": "3400.0",
            "c": "3450.0",
            "h": "3460.0",
            "l": "3390.0",
            "v": "100.0",
            "q": "342000.0",
            "x": True,
        },
    }
    candle = client.parse_binance_message(raw_msg)
    assert candle is not None
    assert candle.symbol == "ETHUSDT"
    assert candle.timeframe == "15m"
    assert candle.close == 3450.0
    assert candle.is_closed is True
    assert len(received_candles) == 1


def test_bybit_ticker_parsing():
    client = PublicWebSocketClient(venue="bybit")
    received_tickers = []
    client.subscribe("ticker", lambda t: received_tickers.append(t))

    raw_msg = {
        "topic": "tickers.SOLUSDT",
        "ts": 1700000000000,
        "data": {
            "symbol": "SOLUSDT",
            "lastPrice": "145.50",
            "bid1Price": "145.40",
            "ask1Price": "145.60",
            "volume24h": "50000.0",
        },
    }
    ticker = client.parse_bybit_message(raw_msg)
    assert ticker is not None
    assert ticker.symbol == "SOLUSDT"
    assert ticker.last_price == 145.50
    assert len(received_tickers) == 1


def test_stale_data_detection():
    client = PublicWebSocketClient(venue="binance", stale_threshold_ms=100)
    # Never received tick is stale
    assert client.is_data_stale("BTCUSDT") is True

    # Fresh tick
    now_ms = int(time.time() * 1000)
    client.last_event_ts_ms["BTCUSDT"] = now_ms
    assert client.is_data_stale("BTCUSDT") is False

    # Old tick
    client.last_event_ts_ms["BTCUSDT"] = now_ms - 200
    assert client.is_data_stale("BTCUSDT") is True


def test_timestamp_inversion_rejected():
    client = PublicWebSocketClient(venue="binance")
    client.last_event_ts_ms["BTCUSDT"] = 1700000005000

    # Inverted timestamp (older than last seen)
    raw_old = {
        "e": "24hrTicker",
        "E": 1700000001000,
        "s": "BTCUSDT",
        "c": "60000.0",
    }
    ticker = client.parse_binance_message(raw_old)
    assert ticker is None
    assert client.dropped_messages == 1


def test_websocket_subscriber_unsubscribe_and_clear():
    client = PublicWebSocketClient(venue="binance")
    ticks_a = []
    ticks_b = []

    cb_a = lambda t: ticks_a.append(t)
    cb_b = lambda t: ticks_b.append(t)

    client.subscribe("ticker", cb_a)
    client.subscribe("ticker", cb_b)

    raw_msg = {
        "e": "24hrTicker",
        "E": 1700000000000,
        "s": "BTCUSDT",
        "c": "50000.0",
        "b": "49999.0",
        "a": "50001.0",
    }
    client.parse_binance_message(raw_msg)
    assert len(ticks_a) == 1
    assert len(ticks_b) == 1

    # Unsubscribe cb_a
    client.unsubscribe("ticker", cb_a)
    raw_msg["E"] = 1700000001000
    client.parse_binance_message(raw_msg)
    assert len(ticks_a) == 1  # Not called
    assert len(ticks_b) == 2  # Called

    # Clear all subscribers
    client.clear_subscribers("ticker")
    raw_msg["E"] = 1700000002000
    client.parse_binance_message(raw_msg)
    assert len(ticks_a) == 1
    assert len(ticks_b) == 2
