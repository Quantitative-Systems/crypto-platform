"""Controlled integration verification test connecting ForwardPaperTradingDaemon to live Binance WebSocket."""
import asyncio
import os
import pytest
from crypto_platform.market_data.websocket_client import PublicWebSocketClient
from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon
from crypto_platform.paper_trading.persistence import SQLitePaperLedger
from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy


@pytest.mark.anyio
async def test_live_public_websocket_forward_paper_session(tmp_path):
    db_file = os.path.join(str(tmp_path), "live_paper_test.db")
    ledger = SQLitePaperLedger(db_path=db_file)

    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_test",
        account_id="acct_paper_live",
        initial_equity=100_000.0,
        ledger=ledger,
    )

    strat = TrendBreakoutStrategy(
        strategy_id="strat_trend_live",
        supported_symbols=["BTCUSDT", "ETHUSDT"],
    )
    daemon.register_strategy(strat)

    ws_client = PublicWebSocketClient(venue="binance", is_futures=False)

    # Run for 4 seconds on live public feed
    summary = await daemon.run_forward_session(
        duration_seconds=4.0,
        symbols=["BTCUSDT", "ETHUSDT"],
        ws_client=ws_client,
    )

    assert summary["account_id"] == "acct_paper_live"
    assert summary["mode"] == "PAPER"
    assert summary["market_events_processed"] > 0
    assert summary["elapsed_seconds"] >= 3.5

    # Verify SQLite recorded events and snapshots
    latest_eq = ledger.load_latest_equity("acct_paper_live")
    assert latest_eq is not None
    assert latest_eq["equity"] > 0
