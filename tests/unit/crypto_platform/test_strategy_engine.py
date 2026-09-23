"""Tests for Universal Strategy Engine and Strategy Plugins."""
import pytest
import time
from crypto_platform.core.events import CandleEvent
from crypto_platform.strategy_engine.mean_reversion import MeanReversionStrategy
from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy


def test_trend_breakout_strategy_signals():
    strategy = TrendBreakoutStrategy(
        strategy_id="strat_trend",
        lookback=3,
        supported_symbols=["BTCUSDT"],
        risk_per_trade_usd=100.0,
    )
    now_ts = int(time.time() * 1000)

    # Establish baseline channel: high 50,200, low 49,900
    c1 = CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts, close_ts=now_ts+3600000, open=50000, high=50100, low=49900, close=50050, volume=10)
    c2 = CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts+3600000, close_ts=now_ts+7200000, open=50050, high=50200, low=50000, close=50150, volume=15)
    c3 = CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts+7200000, close_ts=now_ts+10800000, open=50150, high=50180, low=50100, close=50120, volume=12)

    assert len(strategy.on_candle(c1)) == 0
    assert len(strategy.on_candle(c2)) == 0
    assert len(strategy.on_candle(c3)) == 0

    # Breakout candle: close 50,300 > 50,200
    c4 = CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts+10800000, close_ts=now_ts+14400000, open=50120, high=50350, low=50100, close=50300, volume=25)
    intents = strategy.on_candle(c4)
    assert len(intents) == 1
    intent = intents[0]
    assert intent.direction == 1
    assert intent.symbol == "BTCUSDT"
    assert intent.stop_price is not None
    assert intent.stop_price < intent.limit_price
    assert intent.target_price is not None
    assert intent.target_price > intent.limit_price


def test_mean_reversion_strategy_signals():
    strategy = MeanReversionStrategy(
        strategy_id="strat_mr",
        period=4,
        z_threshold=1.5,
        supported_symbols=["ETHUSDT"],
    )
    now_ts = int(time.time() * 1000)

    # Establish baseline around 3,000
    candles = [
        CandleEvent(venue="binance", symbol="ETHUSDT", timeframe="1h", open_ts=now_ts, close_ts=now_ts+3600000, open=3000, high=3010, low=2990, close=3000, volume=10),
        CandleEvent(venue="binance", symbol="ETHUSDT", timeframe="1h", open_ts=now_ts+3600000, close_ts=now_ts+7200000, open=3000, high=3010, low=2990, close=3005, volume=10),
        CandleEvent(venue="binance", symbol="ETHUSDT", timeframe="1h", open_ts=now_ts+7200000, close_ts=now_ts+10800000, open=3005, high=3015, low=2995, close=2998, volume=10),
        CandleEvent(venue="binance", symbol="ETHUSDT", timeframe="1h", open_ts=now_ts+10800000, close_ts=now_ts+14400000, open=2998, high=3005, low=2995, close=3002, volume=10),
    ]
    for c in candles:
        assert len(strategy.on_candle(c)) == 0

    # Sharp dump: price drops to 2,850 (extreme oversold z-score)
    dump_candle = CandleEvent(venue="binance", symbol="ETHUSDT", timeframe="1h", open_ts=now_ts+14400000, close_ts=now_ts+18000000, open=3002, high=3002, low=2840, close=2850, volume=50)
    intents = strategy.on_candle(dump_candle)
    assert len(intents) == 1
    assert intents[0].direction == 1
    assert "Oversold z-score" in intents[0].signal_reason
