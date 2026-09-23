"""Crypto Trading Platform — Durable SQLite Paper Trading Ledger & Persistence.

Ensures that simulated orders, fills, positions, cash balances, equity curves,
and audit logs are reliably committed to disk and can be restored seamlessly
across daemon restarts without state corruption.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    Fill,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)


class SQLitePaperLedger:
    """ACID-compliant SQLite persistence for Paper Trading."""

    def __init__(self, db_path: str = "paper_trading.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id TEXT PRIMARY KEY,
                    client_order_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    venue TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    time_in_force TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    filled_quantity REAL DEFAULT 0.0,
                    average_fill_price REAL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    rejection_reason TEXT,
                    created_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL
                );
            """)

            # Fills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_fills (
                    fill_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    client_order_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    fee REAL NOT NULL,
                    fee_asset TEXT NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    is_maker INTEGER NOT NULL
                );
            """)

            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction INTEGER NOT NULL,
                    size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    mark_price REAL NOT NULL,
                    unrealized_pnl REAL DEFAULT 0.0,
                    realized_pnl REAL DEFAULT 0.0,
                    updated_at_ms INTEGER NOT NULL,
                    PRIMARY KEY (account_id, symbol)
                );
            """)

            # Equity snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_equity_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    equity REAL NOT NULL,
                    peak_equity REAL NOT NULL,
                    drawdown_pct REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    total_fees REAL NOT NULL
                );
            """)

            # Audit events log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT
                );
            """)

            conn.commit()

    def save_order(self, order: ExecutionOrder, account_id: str = "acct_paper_01") -> None:
        """Persist or update an order."""
        now_ms = int(time.time() * 1000)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_orders (
                    order_id, client_order_id, tenant_id, account_id, venue,
                    symbol, side, order_type, time_in_force, quantity, price,
                    filled_quantity, average_fill_price, status, rejection_reason,
                    created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    filled_quantity = excluded.filled_quantity,
                    average_fill_price = excluded.average_fill_price,
                    status = excluded.status,
                    rejection_reason = excluded.rejection_reason,
                    updated_at_ms = excluded.updated_at_ms;
                """,
                (
                    order.order_id,
                    order.client_order_id,
                    order.tenant_id,
                    account_id,
                    order.venue,
                    order.symbol,
                    order.side.value,
                    order.order_type.value,
                    order.time_in_force.value,
                    order.quantity,
                    order.price,
                    order.filled_quantity,
                    order.average_fill_price,
                    order.status.value,
                    order.rejection_reason,
                    order.created_at_ms,
                    now_ms,
                ),
            )
            conn.commit()

    def record_fill(self, fill: Fill, account_id: str = "acct_paper_01") -> None:
        """Persist a trade fill."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO paper_fills (
                    fill_id, order_id, client_order_id, account_id, symbol, side,
                    price, quantity, fee, fee_asset, timestamp_ms, is_maker
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    fill.fill_id,
                    fill.order_id,
                    fill.client_order_id,
                    account_id,
                    fill.symbol,
                    fill.side.value,
                    fill.price,
                    fill.quantity,
                    fill.fee,
                    fill.fee_asset,
                    fill.timestamp_ms,
                    1 if fill.is_maker else 0,
                ),
            )
            conn.commit()

    def save_position(self, position: Position, account_id: str = "acct_paper_01") -> None:
        """Persist current position state."""
        now_ms = int(time.time() * 1000)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_positions (
                    account_id, symbol, direction, size, entry_price,
                    mark_price, unrealized_pnl, realized_pnl, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, symbol) DO UPDATE SET
                    direction = excluded.direction,
                    size = excluded.size,
                    entry_price = excluded.entry_price,
                    mark_price = excluded.mark_price,
                    unrealized_pnl = excluded.unrealized_pnl,
                    realized_pnl = excluded.realized_pnl,
                    updated_at_ms = excluded.updated_at_ms;
                """,
                (
                    account_id,
                    position.symbol,
                    position.direction,
                    position.size,
                    position.entry_price,
                    position.mark_price,
                    position.unrealized_pnl,
                    position.realized_pnl,
                    now_ms,
                ),
            )
            conn.commit()

    def record_equity_snapshot(
        self,
        account_id: str,
        timestamp_ms: int,
        equity: float,
        peak_equity: float,
        drawdown_pct: float,
        realized_pnl: float,
        total_fees: float,
    ) -> None:
        """Persist an equity curve snapshot."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_equity_history (
                    account_id, timestamp_ms, equity, peak_equity,
                    drawdown_pct, realized_pnl, total_fees
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    account_id,
                    timestamp_ms,
                    equity,
                    peak_equity,
                    drawdown_pct,
                    realized_pnl,
                    total_fees,
                ),
            )
            conn.commit()

    def log_audit_event(
        self,
        account_id: str,
        event_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an operational or risk audit event."""
        now_ms = int(time.time() * 1000)
        details_json = json.dumps(details or {})
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_audit_log (
                    account_id, timestamp_ms, event_type, severity, message, details_json
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (account_id, now_ms, event_type, severity, message, details_json),
            )
            conn.commit()

    def load_positions(self, account_id: str = "acct_paper_01") -> Dict[str, Position]:
        """Restore active positions from disk."""
        positions: Dict[str, Position] = {}
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE account_id = ? AND size > 0;",
                (account_id,),
            ).fetchall()
            for r in rows:
                pos = Position(
                    symbol=r["symbol"],
                    direction=r["direction"],
                    size=r["size"],
                    entry_price=r["entry_price"],
                    mark_price=r["mark_price"],
                    unrealized_pnl=r["unrealized_pnl"],
                    realized_pnl=r["realized_pnl"],
                )
                positions[pos.symbol] = pos
        return positions

    def load_latest_equity(self, account_id: str = "acct_paper_01") -> Optional[Dict[str, float]]:
        """Restore latest equity state."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT equity, peak_equity, drawdown_pct, realized_pnl, total_fees
                FROM paper_equity_history
                WHERE account_id = ?
                ORDER BY timestamp_ms DESC LIMIT 1;
                """,
                (account_id,),
            ).fetchone()
            if row:
                return dict(row)
        return None

    def load_fills(self, account_id: str = "acct_paper_01") -> List[Fill]:
        """Restore fills history."""
        fills: List[Fill] = []
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_fills WHERE account_id = ? ORDER BY timestamp_ms ASC;",
                (account_id,),
            ).fetchall()
            for r in rows:
                f = Fill(
                    fill_id=r["fill_id"],
                    order_id=r["order_id"],
                    client_order_id=r["client_order_id"],
                    symbol=r["symbol"],
                    side=OrderSide(r["side"]),
                    price=r["price"],
                    quantity=r["quantity"],
                    fee=r["fee"],
                    fee_asset=r["fee_asset"],
                    timestamp_ms=r["timestamp_ms"],
                    is_maker=bool(r["is_maker"]),
                )
                fills.append(f)
        return fills
