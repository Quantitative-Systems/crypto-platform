"""
Product 07 — Production Service & Reliability
State Persistence Engine.
Provides atomic disk persistence and instant crash recovery for active candidates, positions, and risk state.
"""

import os
import json
import sqlite3
import time
from typing import Dict, Any, Optional


class StateStore:
    """
    Atomic SQLite state store guaranteeing zero-state-drift crash recovery.
    """

    def __init__(self, db_path: str = "production_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    updated_at_utc INTEGER
                )
            """)
            conn.commit()

    def save_state(self, state_key: str, data: Dict[str, Any]) -> None:
        """
        Persists state dictionary atomically.
        """
        now_ts = int(time.time())
        val_str = json.dumps(data)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_state (key, value_json, updated_at_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at_utc = excluded.updated_at_utc
            """, (state_key, val_str, now_ts))
            conn.commit()

    def load_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """
        Loads persisted state dictionary. Returns None if key does not exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value_json FROM system_state WHERE key = ?", (state_key,))
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
        return None

    def clear_state(self, state_key: Optional[str] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if state_key:
                cursor.execute("DELETE FROM system_state WHERE key = ?", (state_key,))
            else:
                cursor.execute("DELETE FROM system_state")
            conn.commit()
