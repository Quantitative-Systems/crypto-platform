"""Tests for Forward Real-Time Paper Trading Engine and Microstructure Simulator."""
import json
import os
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
from crypto_platform.risk_engine.firewall import RiskFirewall
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
    firewall = RiskFirewall(max_market_data_age_ms=60_000, max_clock_drift_ms=60_000)
    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_test",
        account_id="acc_paper_test",
        initial_equity=50_000.0,
        risk_firewall=firewall,
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


def test_daemon_disconnect_market_data():
    from crypto_platform.market_data.websocket_client import PublicWebSocketClient
    daemon = ForwardPaperTradingDaemon(account_id="acc_disconnect_test")
    ws_client = PublicWebSocketClient(venue="binance")

    daemon.connect_market_data(ws_client)
    assert daemon.on_ticker in ws_client._subscribers.get("ticker", [])
    assert daemon.on_candle in ws_client._subscribers.get("candle", [])

    daemon.disconnect_market_data(ws_client)
    assert daemon.on_ticker not in ws_client._subscribers.get("ticker", [])
    assert daemon.on_candle not in ws_client._subscribers.get("candle", [])


@pytest.mark.anyio
async def test_daemon_run_forward_session_snapshot(tmp_path):
    summary_file = str(tmp_path / "forward_summary_test.json")
    daemon = ForwardPaperTradingDaemon(account_id="acc_snapshot_test")

    # Short session without ws_client should produce summary file and return summary dict
    summary = await daemon.run_forward_session(
        duration_seconds=0.1,
        symbols=["BTCUSDT"],
        summary_out_path=summary_file,
    )
    assert summary["account_id"] == "acc_snapshot_test"
    assert summary["mode"] == "PAPER"
    assert os.path.exists(summary_file)
    with open(summary_file, "r") as f:
        data = json.load(f)
    assert data["account_id"] == "acc_snapshot_test"


def test_microstructure_queue_clearance_and_adverse_selection():
    sim = MicrostructurePaperSimulator(
        maker_queue_clearance_pct=0.0,  # 0% chance on touch alone
        adverse_selection_bps=2.0,
    )
    ticker_touch = TickerEvent(
        venue="binance", symbol="BTCUSDT", timestamp_ms=1000,
        bid=59990.0, ask=60010.0, last_price=60000.0,
    )
    order = ExecutionOrder(
        order_id="o_limit", client_order_id="c_limit", tenant_id="t1", account_id="a1",
        venue="binance", symbol="BTCUSDT", side=OrderSide.BUY,
        order_type=OrderType.LIMIT, time_in_force=TimeInForce.GTC,
        quantity=0.1, price=60000.0,
    )
    # Price touched but queue not cleared -> Unfilled
    fill = sim.process_order(order, ticker_touch)
    assert fill is None

    # Price traded strictly through (bid 59970, ask 60010, last_price 59980) -> Guaranteed fill as maker
    ticker_through = TickerEvent(
        venue="binance", symbol="BTCUSDT", timestamp_ms=2000,
        bid=59970.0, ask=60010.0, last_price=59980.0,
    )
    fill_through = sim.process_order(order, ticker_through)
    assert fill_through is not None
    assert fill_through.is_maker is True
    # Fill price reflects adverse selection above limit price
    assert fill_through.price >= 60000.0


def test_microstructure_partial_fill_on_large_order():
    sim = MicrostructurePaperSimulator(
        depth_liquidity_usd=100_000.0,
        partial_fill_threshold_pct=0.10,  # > $10,000 order triggers partial fill
    )
    ticker = TickerEvent(
        venue="binance", symbol="BTCUSDT", timestamp_ms=1000,
        bid=50000.0, ask=50002.0, last_price=50001.0,
    )
    # Order notional = 1.0 BTC * 50,002 = $50,002 (> 10% of $100k depth)
    order = ExecutionOrder(
        order_id="o_large", client_order_id="c_large", tenant_id="t1", account_id="a1",
        venue="binance", symbol="BTCUSDT", side=OrderSide.BUY,
        order_type=OrderType.MARKET, time_in_force=TimeInForce.IOC,
        quantity=1.0, price=None,
    )
    fill = sim.process_order(order, ticker)
    assert fill is not None
    assert fill.quantity < 1.0  # Partial fill executed
    assert fill.quantity > 0.0


def test_daemon_unclosed_and_duplicate_candle_filtering():
    daemon = ForwardPaperTradingDaemon(account_id="acc_candle_filter")
    strat = TrendBreakoutStrategy(strategy_id="strat_filter", lookback=2, supported_symbols=["BTCUSDT"])
    daemon.register_strategy(strat)

    now_ts = int(time.time() * 1000)
    unclosed_candle = CandleEvent(
        venue="binance", symbol="BTCUSDT", timeframe="15m",
        open_ts=now_ts - 900000, close_ts=now_ts, open=50000, high=51000, low=49000, close=50500, volume=10,
        is_closed=False,
    )
    # Unclosed candle should be completely ignored
    orders = daemon.on_candle(unclosed_candle)
    assert len(orders) == 0

    closed_candle = CandleEvent(
        venue="binance", symbol="BTCUSDT", timeframe="15m",
        open_ts=now_ts - 900000, close_ts=now_ts, open=50000, high=51000, low=49000, close=50500, volume=10,
        is_closed=True,
    )
    daemon.on_candle(closed_candle)
    assert len(daemon._processed_candle_keys) == 1

    # Exact duplicate delivery of the same closed candle must be rejected
    orders_dup = daemon.on_candle(closed_candle)
    assert len(orders_dup) == 0


def test_daemon_ioc_cancellation_when_unfilled():
    daemon = ForwardPaperTradingDaemon(account_id="acc_ioc_cancel")
    now_ts = int(time.time() * 1000)
    ticker = TickerEvent(venue="binance", symbol="BTCUSDT", timestamp_ms=now_ts, bid=50000, ask=50010, last_price=50005)
    daemon.latest_tickers["BTCUSDT"] = ticker

    # Dummy strategy that emits an IOC emergency intent
    class DummyIOCStrategy:
        strategy_id = "s_ioc"
        def on_candle(self, c):
            return [
                OrderIntent(
                    intent_id="i_ioc_1", strategy_id="s_ioc", tenant_id="t1", account_id="acc_ioc_cancel",
                    symbol="BTCUSDT", direction=1, target_size=0.1, urgency=ExecutionUrgency.EMERGENCY,
                )
            ]
        def on_fill(self, f):
            pass

    daemon.register_strategy(DummyIOCStrategy())
    # Force simulator to return None (no liquidity / fill fails)
    daemon.simulator.process_order = lambda o, t: None

    candle = CandleEvent(
        venue="binance", symbol="BTCUSDT", timeframe="15m",
        open_ts=now_ts - 1000, close_ts=now_ts, open=50000, high=50010, low=49990, close=50005, volume=10,
        is_closed=True,
    )
    orders = daemon.on_candle(candle)
    assert len(orders) == 1
    order = orders[0]

    # Check order was cancelled and not left hanging in open orders
    open_orders = daemon.oms.get_open_orders("acc_ioc_cancel")
    assert order.order_id not in [o.order_id for o in open_orders]
    assert order.status == OrderStatus.CANCELLED


def test_daemon_execution_funnel_and_rejections():
    daemon = ForwardPaperTradingDaemon(account_id="acc_funnel_test")
    strat = TrendBreakoutStrategy(strategy_id="strat_trend_funnel", lookback=10, supported_symbols=["BTCUSDT"])
    daemon.register_strategy(strat)

    now_ts = int(time.time() * 1000)

    # 1. Unclosed candle rejected
    unclosed = CandleEvent(
        venue="binance", symbol="BTCUSDT", timeframe="15m",
        open_ts=now_ts - 1000, close_ts=now_ts, open=50000, high=50010, low=49990, close=50005, volume=10,
        is_closed=False,
    )
    res = daemon.on_candle(unclosed)
    assert len(res) == 0
    assert daemon.funnel.unclosed_candles == 1
    assert daemon.funnel.rejection_reasons["UNCLOSED_CANDLE"] == 1

    # 2. Closed candle with insufficient lookback
    closed_1 = CandleEvent(
        venue="binance", symbol="BTCUSDT", timeframe="15m",
        open_ts=now_ts - 2000, close_ts=now_ts - 1000, open=50000, high=50010, low=49990, close=50005, volume=10,
        is_closed=True,
    )
    res_1 = daemon.on_candle(closed_1)
    assert len(res_1) == 0
    assert daemon.funnel.closed_candles == 1
    assert daemon.funnel.strategy_evaluations == 1
    assert daemon.funnel.rejection_reasons.get("INSUFFICIENT_LOOKBACK", 0) >= 1

    # 3. Duplicate closed candle rejected
    res_dup = daemon.on_candle(closed_1)
    assert len(res_dup) == 0
    assert daemon.funnel.duplicate_candles == 1
    assert daemon.funnel.rejection_reasons["DUPLICATE_CANDLE"] == 1


def test_daemon_warm_up_lookback_loading():
    from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy, TrendRiderStrategy
    from crypto_platform.strategy_engine.funding_carry import FundingCarryStrategy

    daemon = ForwardPaperTradingDaemon(account_id="acc_warmup_test")
    s_trend = TrendBreakoutStrategy("t_eth", horizon="INTRADAY", supported_symbols=["ETHUSDT"], lookback=20)
    s_rider = TrendRiderStrategy("r_doge", horizon="POSITION", supported_symbols=["DOGEUSDT"])
    s_carry = FundingCarryStrategy("c_carry", horizon="CARRY", supported_symbols=["ETHUSDT"])

    daemon.register_strategy(s_trend)
    daemon.register_strategy(s_rider)
    daemon.register_strategy(s_carry)

    loaded = daemon.warm_up(cache_dir="market_data/cache", bars=30)
    assert loaded["t_eth"] >= 21
    assert len(s_trend.recent_candles["ETHUSDT"]) >= 21
    assert loaded["r_doge"] >= 30
    assert len(s_rider.recent_candles["DOGEUSDT"]) >= 30
    assert loaded["c_carry"] >= 6
    assert len(s_carry._funding_rates["ETHUSDT"]) >= 6


def test_daemon_funding_rate_evaluation():
    from crypto_platform.core.events import FundingRateEvent
    from crypto_platform.strategy_engine.funding_carry import FundingCarryStrategy

    daemon = ForwardPaperTradingDaemon(account_id="acc_carry_test")
    strat = FundingCarryStrategy("carry_eth", supported_symbols=["ETHUSDT"], min_entry_apr=0.05)
    daemon.register_strategy(strat)

    now_ts = int(time.time() * 1000)

    # Feed 7 funding events with positive 0.05% rate (54.7% APR)
    orders = []
    for i in range(7):
        evt = FundingRateEvent(
            venue="binance",
            symbol="ETHUSDT",
            timestamp_ms=now_ts + i * 28800000,
            funding_rate=0.0005,
            mark_price=2500.0,
            index_price=2500.0,
            next_funding_time_ms=now_ts + (i + 1) * 28800000,
        )
        res = daemon.on_funding_rate(evt)
        orders.extend(res)

    assert len(orders) > 0
    assert daemon.funnel.signals > 0
    assert daemon.funnel.simulator_submissions > 0
    assert daemon.funnel.full_fills + daemon.funnel.resting_orders > 0

    # Verify structured audit trail was recorded
    assert len(daemon.trade_audit_trail) > 0
    rec = daemon.trade_audit_trail[0]
    assert rec["strategy_id"] == "carry_eth"
    assert rec["symbol"] == "ETHUSDT"
    assert "signal_timestamp_ms" in rec
    assert "spread" in rec
    assert "latency_ms" in rec
    assert rec["latency_ms"] >= 0.0


