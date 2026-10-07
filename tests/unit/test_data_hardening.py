"""Unit tests for Market Data Hardening (clock drift, candle gap detection, deduplication)."""
import time
import pytest
from market_data.realtime.binance_ws_client import (
    BinanceRealtimeWSClient,
    DataHealthStatus,
)


def test_binance_ws_clock_drift_evaluation():
    client = BinanceRealtimeWSClient(symbols=["BTCUSDT"], max_clock_drift_ms=1000)
    client._metrics["BTCUSDT"].connected = True
    client._metrics["BTCUSDT"].last_heartbeat_time = time.time()
    now_ms = int(time.time() * 1000)

    # Within tolerance (200ms)
    assert client.evaluate_clock_drift(local_time_ms=now_ms, server_time_ms=now_ms + 200) is True
    metrics = client.get_metrics_snapshot()["BTCUSDT"]
    assert metrics["clock_drift_ms"] == 200

    # Exceeds tolerance (1500ms)
    assert client.evaluate_clock_drift(local_time_ms=now_ms, server_time_ms=now_ms + 1500) is False
    assert client.get_feed_health("BTCUSDT") == DataHealthStatus.DATA_DEGRADED
    metrics = client.get_metrics_snapshot()["BTCUSDT"]
    assert metrics["clock_drift_ms"] == 1500


def test_binance_ws_candle_gap_detection():
    client = BinanceRealtimeWSClient(symbols=["BTCUSDT"], base_timeframe="15m")
    gap_events = []

    def on_gap(sym: str, start_ts: int, end_ts: int):
        gap_events.append((sym, start_ts, end_ts))

    client.add_gap_listener(on_gap)

    # Candle 1: ts = 1000000
    msg_1 = {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1_000_000_000,
            "T": 1_000_899_999,
            "o": "50000.0",
            "h": "50100.0",
            "l": "49900.0",
            "c": "50050.0",
            "v": "10.0",
            "x": True,  # closed
        },
    }
    client._handle_raw_message(str(msg_1).replace("'", '"').replace("True", "true"))
    assert len(gap_events) == 0

    # Candle 2: skips 2 periods (15m is 900,000ms, skips to 1,000,000,000 + 3 * 900,000)
    skipped_ts = 1_000_000_000 + (3 * 900_000)
    msg_2 = {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": skipped_ts,
            "T": skipped_ts + 899_999,
            "o": "50050.0",
            "h": "50200.0",
            "l": "50000.0",
            "c": "50150.0",
            "v": "15.0",
            "x": True,
        },
    }
    client._handle_raw_message(str(msg_2).replace("'", '"').replace("True", "true"))

    assert len(gap_events) == 1
    sym, start_ts, end_ts = gap_events[0]
    assert sym == "BTCUSDT"
    assert start_ts == 1_000_000_000 + 900_000
    metrics = client.get_metrics_snapshot()["BTCUSDT"]
    assert metrics["gaps_detected"] == 1
