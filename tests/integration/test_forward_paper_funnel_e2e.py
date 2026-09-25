"""End-to-End Verification of the Forward-Paper Execution Funnel across all 10 Promoted Books."""
import os
import time
import pytest
from crypto_platform.core.events import CandleEvent, TickerEvent
from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon
from crypto_platform.paper_trading.persistence import SQLitePaperLedger
from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy, TrendRiderStrategy
from crypto_platform.strategy_engine.mean_reversion import BollingerMeanReversionStrategy
from crypto_platform.strategy_engine.funding_carry import FundingCarryStrategy


def test_forward_paper_funnel_all_10_books_e2e(tmp_path):
    db_file = os.path.join(str(tmp_path), "funnel_e2e.db")
    ledger = SQLitePaperLedger(db_path=db_file)

    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_e2e",
        account_id="acc_funnel_e2e",
        initial_equity=200_000.0,
        ledger=ledger,
    )

    # 1. Register all 10 promoted books
    daemon.register_strategy(TrendBreakoutStrategy("promoted_intraday_trend_eth", horizon="INTRADAY", supported_symbols=["ETHUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_intraday_trend_sol", horizon="INTRADAY", supported_symbols=["SOLUSDT"]))
    daemon.register_strategy(BollingerMeanReversionStrategy("promoted_intraday_mr_ada", horizon="INTRADAY", supported_symbols=["ADAUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_eth", horizon="SWING", supported_symbols=["ETHUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_sol", horizon="SWING", supported_symbols=["SOLUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_ada", horizon="SWING", supported_symbols=["ADAUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_pos_trend_bnb", horizon="POSITION", supported_symbols=["BNBUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_pos_trend_ada", horizon="POSITION", supported_symbols=["ADAUSDT"]))
    daemon.register_strategy(TrendRiderStrategy("promoted_pos_rider_doge", horizon="POSITION", supported_symbols=["DOGEUSDT"]))
    daemon.register_strategy(FundingCarryStrategy("promoted_carry_portfolio", horizon="CARRY", supported_symbols=["ETHUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT", "DOGEUSDT"]))

    assert len(daemon.strategies) == 10

    # 2. Pre-warm strategy lookbacks from certified cache
    loaded = daemon.warm_up(cache_dir="market_data/cache", bars=30)
    for strat_id, count in loaded.items():
        assert count > 0, f"Strategy {strat_id} lookback was not pre-warmed!"

    now_ts = int(time.time() * 1000)

    # 3. Simulate arrival of unclosed candle -> funnel unclosed_candles incremented
    unclosed = CandleEvent(
        venue="binance", symbol="ETHUSDT", timeframe="15m",
        open_ts=now_ts - 1000, close_ts=now_ts, open=2500, high=2510, low=2490, close=2505, volume=100,
        is_closed=False,
    )
    res_unclosed = daemon.on_candle(unclosed)
    assert len(res_unclosed) == 0
    assert daemon.funnel.unclosed_candles == 1

    # 4. Simulate arrival of a closed candle that does not break channel -> NO_SIGNAL recorded
    closed_normal = CandleEvent(
        venue="binance", symbol="ETHUSDT", timeframe="15m",
        open_ts=now_ts - 2000, close_ts=now_ts - 1000, open=2500, high=2510, low=2490, close=2500, volume=100,
        is_closed=True,
    )
    daemon.on_candle(closed_normal)
    assert daemon.funnel.closed_candles == 1
    assert daemon.funnel.rejection_reasons.get("NO_SIGNAL", 0) > 0

    # 5. Simulate arrival of a realistic 20-bar Donchian breakout -> SIGNAL & ORDER generated
    eth_history = daemon.strategies["promoted_intraday_trend_eth"].recent_candles["ETHUSDT"]
    highest_h = max(c.high for c in eth_history[-20:])
    breakout_price = highest_h + 5.0  # Just above the 20-bar channel

    # Provide market ticker aligned with current price
    daemon.latest_tickers["ETHUSDT"] = TickerEvent(
        venue="binance", symbol="ETHUSDT", timestamp_ms=now_ts,
        bid=breakout_price * 0.9999, ask=breakout_price * 1.0001, last_price=breakout_price,
    )

    closed_breakout = CandleEvent(
        venue="binance", symbol="ETHUSDT", timeframe="15m",
        open_ts=now_ts - 1000, close_ts=now_ts, open=breakout_price - 2, high=breakout_price + 3,
        low=breakout_price - 5, close=breakout_price, volume=1000,
        is_closed=True,
    )
    orders = daemon.on_candle(closed_breakout)

    # Verify complete funnel path to submission
    assert daemon.funnel.signals > 0
    assert daemon.funnel.order_intents > 0
    assert daemon.funnel.oms_acceptances > 0
    assert daemon.funnel.simulator_submissions > 0
    assert daemon.funnel.full_fills + daemon.funnel.resting_orders > 0

    # 6. Verify summary snapshot contains complete funnel metrics
    summary = daemon.get_summary()
    assert "funnel" in summary
    assert summary["funnel"]["market_events"] > 0
    assert summary["funnel"]["closed_candles"] > 0
    assert summary["funnel"]["strategy_evaluations"] > 0
    assert "trade_records" in summary
    assert len(summary["trade_records"]) > 0
    assert "signal_timestamp_ms" in summary["trade_records"][0]
