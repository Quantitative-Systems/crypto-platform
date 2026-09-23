"""Unit tests for the Strategy Engine plugin framework."""
import time
import pytest
from crypto_platform.core.events import CandleEvent, FundingRateEvent
from crypto_platform.strategy_engine import (
    BollingerMeanReversionStrategy,
    FundingCarryStrategy,
    MomentumStrategy,
    PairsTradingStrategy,
    SystematicInvestingStrategy,
    TrendBreakoutStrategy,
    VolatilityExpansionStrategy,
)


def _make_candle(symbol: str, close: float, high: float = 0.0, low: float = 0.0, open_p: float = 0.0, ts: int = 0) -> CandleEvent:
    t = ts or int(time.time() * 1000)
    h = high if high > 0 else close * 1.01
    l = low if low > 0 else close * 0.99
    o = open_p if open_p > 0 else close
    return CandleEvent(
        venue="binance",
        symbol=symbol,
        timeframe="15m",
        open_ts=t - 900000,
        close_ts=t,
        open=o,
        high=h,
        low=l,
        close=close,
        volume=100.0,
    )


def test_momentum_strategy_generates_intents():
    strat = MomentumStrategy(lookback_bars=5, momentum_threshold_pct=0.01)
    # Feed flat candles then a surge
    intents = []
    base_ts = 1700000000000
    for i in range(5):
        intents = strat.on_candle(_make_candle("BTCUSDT", 60000.0, ts=base_ts + i * 900000))

    assert len(intents) == 0

    # 6th candle surges +3%
    intents = strat.on_candle(_make_candle("BTCUSDT", 61800.0, ts=base_ts + 6 * 900000))
    assert len(intents) == 1
    assert intents[0].direction == 1
    assert intents[0].symbol == "BTCUSDT"
    assert "Bullish momentum" in intents[0].signal_reason


def test_pairs_trading_strategy_spread_divergence():
    strat = PairsTradingStrategy(asset_a="ETHUSDT", asset_b="BTCUSDT", lookback_bars=10, z_threshold=1.5)
    base_ts = 1700000000000

    # Normal ratio ~ 0.05 (3000 / 60000)
    for i in range(15):
        strat.on_candle(_make_candle("ETHUSDT", 3000.0, ts=base_ts + i * 900000))
        strat.on_candle(_make_candle("BTCUSDT", 60000.0, ts=base_ts + i * 900000))

    # ETH spikes to 3300 while BTC drops to 58000 -> ratio jumps to 0.0569 (divergence)
    strat.on_candle(_make_candle("BTCUSDT", 58000.0, ts=base_ts + 16 * 900000))
    intents = strat.on_candle(_make_candle("ETHUSDT", 3300.0, ts=base_ts + 16 * 900000))

    assert len(intents) == 1
    # Spread high -> Short ETH (direction -1)
    assert intents[0].direction == -1
    assert intents[0].symbol == "ETHUSDT"


def test_funding_carry_strategy_entry_and_exit():
    strat = FundingCarryStrategy(min_entry_apr=0.08, min_exit_apr=0.02)
    now_ms = int(time.time() * 1000)

    # High funding rate: 0.0003 per 8h = 32.85% APR
    high_event = FundingRateEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms,
        funding_rate=0.0003,
        mark_price=60000.0,
        index_price=60000.0,
        next_funding_time_ms=now_ms + 28800000,
    )
    # Feed 7 events
    intents = []
    for _ in range(7):
        intents = strat.on_funding_rate(high_event)

    assert len(intents) == 1
    # Enters short perp to receive funding
    assert intents[0].direction == -1
    assert intents[0].symbol == "BTCUSDT"

    # Simulate fill
    from crypto_platform.core.domain import Fill, OrderSide
    strat.on_fill(
        Fill(
            fill_id="f_carry_1",
            order_id="o_1",
            client_order_id="c_1",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            price=60000.0,
            quantity=intents[0].target_size,
            fee=5.0,
            fee_asset="USDT",
            timestamp_ms=now_ms,
            is_maker=False,
        )
    )

    # Now funding compresses to negative
    neg_event = FundingRateEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms + 1000,
        funding_rate=-0.0001,
        mark_price=60000.0,
        index_price=60000.0,
        next_funding_time_ms=now_ms + 28800000,
    )
    for _ in range(25):
        intents = strat.on_funding_rate(neg_event)

    assert len(intents) == 1
    # Exits by buying to close
    assert intents[0].direction == 1
    assert "exit" in intents[0].signal_reason.lower()


def test_volatility_expansion_strategy():
    strat = VolatilityExpansionStrategy(atr_period=5, expansion_factor=1.5)
    base_ts = 1700000000000

    # Quiet candles: range = 10
    for i in range(7):
        strat.on_candle(_make_candle("BTCUSDT", 60000.0, high=60005.0, low=59995.0, ts=base_ts + i * 900000))

    # Giant expansion candle: range = 50, closed up
    intents = strat.on_candle(
        _make_candle("BTCUSDT", 60040.0, high=60045.0, low=59995.0, open_p=60000.0, ts=base_ts + 8 * 900000)
    )
    assert len(intents) == 1
    assert intents[0].direction == 1
    assert "expansion" in intents[0].signal_reason.lower()


def test_systematic_investing_dca():
    strat = SystematicInvestingStrategy(interval_bars=5, ma_filter_bars=5)
    base_ts = 1700000000000

    intents = []
    for i in range(5):
        intents = strat.on_candle(_make_candle("BTCUSDT", 60000.0, ts=base_ts + i * 900000))

    assert len(intents) == 1
    assert intents[0].direction == 1
    assert intents[0].symbol == "BTCUSDT"
    assert "DCA" in intents[0].signal_reason
