"""Unit tests for Continuous 7-Timeframe Candle Engine."""
import numpy as np
import pytest

from market_data.realtime.candle_engine import (
    CandleRecord,
    ContinuousCandleEngine,
)


def test_continuous_candle_engine_ingest_and_causality():
    engine = ContinuousCandleEngine(symbols=["BTCUSDT"])
    c1 = CandleRecord(
        symbol="BTCUSDT",
        timeframe="15m",
        open_ts=1000,
        close_ts=1900,
        open=60000.0,
        high=60500.0,
        low=59800.0,
        close=60200.0,
        volume=10.0,
    )
    engine.ingest_closed_candle(c1)

    data = engine.get_timeframe_data("BTCUSDT", "15m")
    assert data is not None
    assert len(data["c"]) == 1
    assert data["c"][0] == 60200.0

    # Ingest duplicate candle -> should be dropped
    engine.ingest_closed_candle(c1)
    data = engine.get_timeframe_data("BTCUSDT", "15m")
    assert len(data["c"]) == 1

    # Ingest next bar causally
    c2 = CandleRecord(
        symbol="BTCUSDT",
        timeframe="15m",
        open_ts=2000,
        close_ts=2900,
        open=60200.0,
        high=60800.0,
        low=60100.0,
        close=60700.0,
        volume=15.0,
    )
    engine.ingest_closed_candle(c2)
    data = engine.get_timeframe_data("BTCUSDT", "15m")
    assert len(data["c"]) == 2
    assert data["c"][1] == 60700.0


def test_continuous_candle_engine_disk_cache_seeding():
    engine = ContinuousCandleEngine(symbols=["BTCUSDT"])
    loaded = engine.seed_from_disk_cache("BTCUSDT")
    # Verify that timeframes were seeded from market_data/cache
    assert loaded > 0
    all_data = engine.get_all_timeframe_data("BTCUSDT")
    assert len(all_data) > 0
