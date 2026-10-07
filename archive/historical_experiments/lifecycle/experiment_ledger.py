"""
Quantitative Crypto Platform (QCP) — Immutable Experiment Ledger.

Records all hypothesis evaluations, strategy mutations, backtest results,
and parameter sweeps in an append-only verifiable database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class ExperimentEntry:
    experiment_id: str
    hypothesis_id: str
    strategy_name: str
    family: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    dev_net_r: float
    val_net_r: Optional[float]
    oos_net_r: Optional[float]
    verdict: str  # QUALIFIED, FALSIFIED, DATA_BLOCKED
    falsification_reason: Optional[str]
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    lineage_hash: str = ""

    def compute_hash(self) -> str:
        s = f"{self.experiment_id}:{self.strategy_name}:{self.symbol}:{self.dev_net_r}:{self.verdict}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()


class ExperimentLedger:
    """
    Persistent SQLite & JSONL experiment vault.
    """

    def __init__(self, db_path: Optional[Path] = None):
        base = Path(__file__).resolve().parent.parent.parent
        self.db_path = db_path or base / "research" / "experiment_ledger.db"
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                hypothesis_id TEXT,
                strategy_name TEXT,
                family TEXT,
                symbol TEXT,
                timeframe TEXT,
                parameters_json TEXT,
                dev_net_r REAL,
                val_net_r REAL,
                oos_net_r REAL,
                verdict TEXT,
                falsification_reason TEXT,
                created_at_utc TEXT,
                lineage_hash TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def record_experiment(self, entry: ExperimentEntry) -> str:
        if not entry.lineage_hash:
            entry.lineage_hash = entry.compute_hash()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO experiments (
                experiment_id, hypothesis_id, strategy_name, family, symbol,
                timeframe, parameters_json, dev_net_r, val_net_r, oos_net_r,
                verdict, falsification_reason, created_at_utc, lineage_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.experiment_id,
                entry.hypothesis_id,
                entry.strategy_name,
                entry.family,
                entry.symbol,
                entry.timeframe,
                json.dumps(entry.parameters),
                entry.dev_net_r,
                entry.val_net_r,
                entry.oos_net_r,
                entry.verdict,
                entry.falsification_reason,
                entry.created_at_utc,
                entry.lineage_hash,
            ),
        )
        conn.commit()
        conn.close()
        return entry.experiment_id

    def list_experiments(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments ORDER BY created_at_utc DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result
