"""Tests for Forward Real-Time Paper Trading Engine and Microstructure Simulator."""
import pytest
import time
from crypto_platform.core.domain import (
    ExecutionOrder,
    ExecutionUrgency,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from crypto_platform.core.events import CandleEvent, TickerEvent
from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon
from crypto_platform.paper_trading.simulator import MicrostructurePaperSimulator
from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy


def test_microstructure_market_order_fill():
    sim = MicrostructurePaperSimulator(
        maker_fee_bps=2.0, taker_fee_bps=6.0, base_slippage_bps=1.0
    )
    ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=int(time.time() * 1000),
        bid=60_000.0,
        ask=60_002.0,
        last_price=60_001.0,
    )
    order = ExecutionOrder(
        order_id="o1",
        client_order_id="c1",
        tenant_id="t1",
        account_id="a1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.IOC,
        quantity=1.0,
        price=None,
    )
    fill = sim.process_order(order, ticker)
    assert fill is not None
    # Buy crosses to ask (60,002.0) + slippage
    assert fill.price >= 60_002.0
    assert fill.is_maker is False
    # Taker fee ~ 0.06% of ~60,000 ~ 36 USDT
    assert fill.fee > 30.0


def test_microstructure_post_only_rejection():
    sim = MicrostructurePaperSimulator()
    ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=int(time.time() * 1000),
        bid=60_000.0,
        ask=60_002.0,
        last_price=60_001.0,
    )
    # Buy limit order with price 60,005 (above ask) with POST_ONLY should be rejected
    order = ExecutionOrder(
        order_id="o2",
        client_order_id="c2",
        tenant_id="t1",
        account_id="a1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.POST_ONLY,
        time_in_force=TimeInForce.PO,
        quantity=1.0,
        price=60_005.0,
    )
    fill = sim.process_order(order, ticker)
    assert fill is None  # Post-only rejected because it crosses


def test_forward_paper_trading_daemon_lifecycle():
    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_test",
        account_id="acc_paper_test",
        initial_equity=50_000.0,
    )
    strategy = TrendBreakoutStrategy(
        strategy_id="strat_trend_test",
        lookback=3,
        supported_symbols=["BTCUSDT"],
        risk_per_trade_usd=100.0,
    )
    daemon.register_strategy(strategy)

    now_ts = int(time.time() * 1000)

    # Feed 4 candles establishing a breakout with timestamps within clock-drift tolerance
    candles = [
        CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts-4000, close_ts=now_ts-3000, open=50000, high=50100, low=49900, close=50050, volume=10),
        CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts-3000, close_ts=now_ts-2000, open=50050, high=50200, low=50000, close=50150, volume=15),
        CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts-2000, close_ts=now_ts-1000, open=50150, high=50300, low=50100, close=50250, volume=20),
        CandleEvent(venue="binance", symbol="BTCUSDT", timeframe="1h", open_ts=now_ts-1000, close_ts=now_ts, open=50250, high=50600, low=50200, close=50550, volume=35),
    ]

    orders_generated = []
    for c in candles:
        orders = daemon.on_candle(c)
        orders_generated.extend(orders)

    assert len(orders_generated) > 0
    assert len(daemon.fills_history) > 0

    summary = daemon.get_summary()
    assert summary["mode"] == "PAPER"
    assert summary["total_fills"] > 0
    assert "BTCUSDT" in summary["open_positions"]
