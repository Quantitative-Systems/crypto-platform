"""Unit and integration tests for the forward paper trading soak runner."""
import os
import pytest
from crypto_platform.core.domain import OperatingMode
from crypto_platform.core.events import TickerEvent
from crypto_platform.paper_trading.soak_runner import PaperSoakHarness, LiveTradingDisabledError


def test_soak_harness_initialization(tmp_path):
    db_file = str(tmp_path / "soak_test.db")
    harness = PaperSoakHarness(db_path=db_file)
    daemon = harness.initialize_daemon()

    assert daemon is not None
    assert daemon.account_id == "acct_soak_paper"
    assert daemon.initial_equity == 100_000.0
    assert "soak_trend_btc" in daemon.strategies
    assert "soak_mr_sol" in daemon.strategies


def test_soak_harness_live_order_blocker(tmp_path):
    db_file = str(tmp_path / "soak_blocker.db")
    harness = PaperSoakHarness(db_path=db_file)
    assert harness.verify_live_order_blocker() is True


def test_soak_harness_restart_persistence(tmp_path):
    db_file = str(tmp_path / "soak_restart.db")
    harness1 = PaperSoakHarness(db_path=db_file, initial_equity=50_000.0)
    daemon1 = harness1.initialize_daemon()

    # Feed market ticker and process
    ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=1700000000000,
        bid=50000.0,
        ask=50002.0,
        last_price=50001.0,
    )
    daemon1.on_ticker(ticker)

    # Check persistence file exists
    assert os.path.exists(db_file)

    # Recreate daemon from same SQLite database (Simulating crash / restart)
    harness2 = PaperSoakHarness(db_path=db_file, initial_equity=50_000.0)
    daemon2 = harness2.initialize_daemon()

    summary2 = daemon2.get_summary()
    assert summary2["mode"] == OperatingMode.PAPER.value
    assert summary2["current_equity"] == 50_000.0


@pytest.mark.anyio
async def test_soak_runner_live_websocket_short_run(tmp_path):
    db_file = str(tmp_path / "soak_live.db")
    harness = PaperSoakHarness(db_path=db_file)

    # Run short 2-second live feed soak
    summary = await harness.run_soak_session(duration_seconds=2.0, symbols=["BTCUSDT"], test_restart=False)

    assert summary["mode"] == "PAPER"
    assert summary["live_capital_usd"] == 0.00
    assert summary["live_orders_blocked"] is True
    assert summary["persistence_verified"] is True
