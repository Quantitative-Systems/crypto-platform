"""Unit tests for SQLitePaperLedger and persistent state recovery."""
import os
import time
import pytest
from crypto_platform.core.domain import (
    ExecutionOrder,
    Fill,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)
from crypto_platform.paper_trading.persistence import SQLitePaperLedger
from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon


def test_sqlite_ledger_initialization(tmp_path):
    db_file = os.path.join(str(tmp_path), "test_ledger.db")
    ledger = SQLitePaperLedger(db_path=db_file)
    assert os.path.exists(db_file)


def test_sqlite_ledger_orders_and_fills(tmp_path):
    db_file = os.path.join(str(tmp_path), "test_ledger.db")
    ledger = SQLitePaperLedger(db_path=db_file)

    now_ms = int(time.time() * 1000)
    order = ExecutionOrder(
        order_id="o_test_001",
        client_order_id="c_test_001",
        tenant_id="t_01",
        account_id="acct_paper_01",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.5,
        price=60000.0,
        status=OrderStatus.SUBMITTED,
        created_at_ms=now_ms,
    )
    ledger.save_order(order, account_id="acct_paper_01")

    fill = Fill(
        fill_id="f_001",
        order_id="o_test_001",
        client_order_id="c_test_001",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        price=60000.0,
        quantity=0.5,
        fee=18.0,
        fee_asset="USDT",
        timestamp_ms=now_ms + 10,
        is_maker=False,
    )
    ledger.record_fill(fill, account_id="acct_paper_01")

    # Load fills back
    recovered_fills = ledger.load_fills(account_id="acct_paper_01")
    assert len(recovered_fills) == 1
    assert recovered_fills[0].fill_id == "f_001"
    assert recovered_fills[0].price == 60000.0
    assert recovered_fills[0].quantity == 0.5


def test_sqlite_ledger_positions_and_equity(tmp_path):
    db_file = os.path.join(str(tmp_path), "test_ledger.db")
    ledger = SQLitePaperLedger(db_path=db_file)

    pos = Position(
        symbol="ETHUSDT",
        direction=1,
        size=5.0,
        entry_price=3000.0,
        mark_price=3100.0,
        unrealized_pnl=500.0,
        realized_pnl=100.0,
    )
    ledger.save_position(pos, account_id="acct_paper_01")

    now_ms = int(time.time() * 1000)
    ledger.record_equity_snapshot(
        account_id="acct_paper_01",
        timestamp_ms=now_ms,
        equity=105500.0,
        peak_equity=105500.0,
        drawdown_pct=0.0,
        realized_pnl=100.0,
        total_fees=25.0,
    )

    positions = ledger.load_positions(account_id="acct_paper_01")
    assert "ETHUSDT" in positions
    assert positions["ETHUSDT"].size == 5.0
    assert positions["ETHUSDT"].entry_price == 3000.0

    latest_eq = ledger.load_latest_equity(account_id="acct_paper_01")
    assert latest_eq is not None
    assert latest_eq["equity"] == 105500.0


def test_daemon_crash_recovery(tmp_path):
    db_file = os.path.join(str(tmp_path), "crash_recovery.db")

    # 1. First daemon session creates position and equity
    daemon1 = ForwardPaperTradingDaemon(
        account_id="acct_paper_crash",
        initial_equity=50000.0,
        db_path=db_file,
    )
    # Simulate a position
    pos = Position(
        symbol="SOLUSDT",
        direction=1,
        size=20.0,
        entry_price=150.0,
        mark_price=160.0,
        unrealized_pnl=200.0,
    )
    daemon1.ledger.save_position(pos, "acct_paper_crash")
    now_ms = int(time.time() * 1000)
    daemon1.ledger.record_equity_snapshot(
        account_id="acct_paper_crash",
        timestamp_ms=now_ms,
        equity=50200.0,
        peak_equity=50200.0,
        drawdown_pct=0.0,
        realized_pnl=0.0,
        total_fees=0.0,
    )

    # 2. Daemon restarts from disk
    daemon2 = ForwardPaperTradingDaemon(
        account_id="acct_paper_crash",
        initial_equity=50000.0,
        db_path=db_file,
    )
    assert daemon2.current_equity == 50200.0
    recovered_pos = daemon2.oms.get_positions("acct_paper_crash")
    assert "SOLUSDT" in recovered_pos
    assert recovered_pos["SOLUSDT"].size == 20.0
