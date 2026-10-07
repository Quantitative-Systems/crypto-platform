"""
Product 01: Crypto Platform - Quantitative Research Database Engine
Stores every evaluated bar telemetry and executed trade into SQLite for deep SQL research queries.
"""

import os
import sqlite3
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "research_vault.db")


class ResearchDB:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Initializes relational tables for trade logs and gate telemetry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_trades (
                    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    action TEXT,
                    strategy_type TEXT,
                    raw_entry_price REAL,
                    fill_entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    dollar_risk REAL,
                    initial_rr REAL,
                    pnl_usd REAL,
                    friction_cost_usd REAL,
                    exit_reason TEXT,
                    entry_timestamp INTEGER
                )
            """)

            # Gate Telemetry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gate_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    total_bars INTEGER,
                    gate_1_fails INTEGER,
                    gate_2_fails INTEGER,
                    gate_3_fails INTEGER,
                    gate_4_fails INTEGER,
                    approved_trades INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def log_trade(self, trade_data: Dict[str, Any]):
        """Persists executed trade record into research database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_trades (
                    symbol, action, strategy_type, raw_entry_price, fill_entry_price,
                    exit_price, stop_loss, take_profit, position_size, dollar_risk,
                    initial_rr, pnl_usd, friction_cost_usd, exit_reason, entry_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("symbol"),
                trade_data.get("action"),
                trade_data.get("strategy_type"),
                trade_data.get("raw_entry_price"),
                trade_data.get("fill_entry_price"),
                trade_data.get("exit_price"),
                trade_data.get("sl"),
                trade_data.get("tp"),
                trade_data.get("position_size"),
                trade_data.get("dollar_risk"),
                trade_data.get("initial_rr"),
                trade_data.get("pnl_usd"),
                trade_data.get("friction_cost_usd"),
                trade_data.get("exit_reason"),
                trade_data.get("entry_timestamp")
            ))
            conn.commit()

    def log_telemetry(self, symbol: str, telemetry: Dict[str, Any]):
        """Logs gate funnel rejection counts for an asset run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO gate_telemetry (
                    symbol, total_bars, gate_1_fails, gate_2_fails, gate_3_fails, gate_4_fails, approved_trades
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                telemetry.get("total_bars_evaluated", 0),
                telemetry.get("gate_1_htf_fails", 0),
                telemetry.get("gate_2_mtf_fails", 0),
                telemetry.get("gate_3_ltf_fails", 0),
                telemetry.get("gate_4_risk_fails", 0),
                telemetry.get("trades_approved", 0)
            ))
            conn.commit()