"""Crypto Platform — State Checkpointing & Restart Recovery.

Ensures continuous 24/7/365 resilience by maintaining deterministic, versioned state checkpoints:
- Active open positions & order intents
- Simulated account equity and peak equity
- Processed candle timestamps
- Circuit breaker trip states
- Executed idempotency keys to prevent duplicate order submissions upon restart
- Dual persistence: Durable SQLite table (application_checkpoints) + atomic filesystem backups with SHA-256 checksums
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from enum import Enum

from core.persistence.database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(__file__).resolve().parent.parent.parent / "research" / "results" / "state"


class PersistenceMode(str, Enum):
    """Execution persistence modes."""
    REQUIRED_DURABLE = "REQUIRED_DURABLE"
    FILE_ONLY_DEV = "FILE_ONLY_DEV"


class PersistenceError(RuntimeError):
    """Raised when persistence operations fail under REQUIRED_DURABLE mode."""
    pass


class StatePersistenceManager:
    """Manages atomic, versioned state serialization and restart recovery."""

    CURRENT_SCHEMA_VERSION = 2

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        db_manager: Optional[DatabaseManager] = None,
        db_path: Optional[Union[str, Path]] = None,
        mode: Optional[Union[PersistenceMode, str]] = None,
    ):
        self.state_dir = Path(state_dir) if state_dir else DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.state_dir / "platform_checkpoint.json"
        self.checkpoint_prev_file = self.state_dir / "platform_checkpoint_prev.json"

        # Determine persistence mode
        if mode is None:
            raw_mode = os.environ.get("CRYPTO_PLATFORM_PERSISTENCE_MODE", PersistenceMode.REQUIRED_DURABLE.value)
            try:
                self.mode = PersistenceMode(raw_mode)
            except ValueError:
                self.mode = PersistenceMode.REQUIRED_DURABLE
        elif isinstance(mode, str):
            self.mode = PersistenceMode(mode)
        else:
            self.mode = mode

        self.db: Optional[DatabaseManager] = None
        self._last_save_success: bool = True
        self._last_save_ts: int = 0
        self._last_error: Optional[str] = None
        self._last_checksum: Optional[str] = None

        # Initialize database handle according to mode
        try:
            if db_manager is not None:
                self.db = db_manager
            elif db_path is not None:
                self.db = get_db_manager(db_path=db_path)
            else:
                self.db = get_db_manager()
        except Exception as e:
            if self.mode == PersistenceMode.REQUIRED_DURABLE:
                self._last_error = f"Database initialization failed: {e}"
                logger.critical(f"FATAL: Database unavailable in REQUIRED_DURABLE mode: {e}")
                raise PersistenceError(
                    f"Durable persistence is required but database is unavailable: {e}"
                ) from e
            else:
                logger.warning(f"Database unavailable in FILE_ONLY_DEV mode; using local disk only: {e}")
                self.db = None

    def close(self) -> None:
        """Close persistence database handle."""
        if self.db:
            self.db.close()

    def get_persistence_health(self) -> Dict[str, Any]:
        """Provides operational diagnostics on persistence subsystem health."""
        is_healthy = (
            (self.mode == PersistenceMode.FILE_ONLY_DEV or self.db is not None)
            and self._last_save_success
            and self._last_error is None
        )
        return {
            "mode": self.mode.value,
            "is_durable": self.mode == PersistenceMode.REQUIRED_DURABLE,
            "database_connected": self.db is not None,
            "last_save_success": self._last_save_success,
            "last_save_timestamp_ms": self._last_save_ts,
            "last_checksum": self._last_checksum,
            "last_error": self._last_error,
            "checkpoint_file_exists": self.checkpoint_file.exists(),
            "status": "HEALTHY" if is_healthy else "DEGRADED",
        }

    def save_checkpoint(
        self,
        equity_usd: float,
        peak_equity_usd: float,
        active_positions: Optional[List[Dict[str, Any]]] = None,
        closed_trades_count: int = 0,
        metrics: Optional[Dict[str, Any]] = None,
        candle_sync_timestamps: Optional[Dict[str, int]] = None,
        circuit_breakers_state: Optional[Dict[str, Any]] = None,
        idempotency_keys: Optional[List[str]] = None,
        closed_positions: Optional[List[Dict[str, Any]]] = None,
        orders_history: Optional[List[Dict[str, Any]]] = None,
        schema_version: int = CURRENT_SCHEMA_VERSION,
    ) -> bool:
        """Atomically save platform state to database and disk with SHA-256 checksum."""
        try:
            timestamp_ms = int(time.time() * 1000)
            idemp_list = list(idempotency_keys or [])
            pos_list = list(active_positions or [])
            met_dict = metrics or {}
            candle_dict = candle_sync_timestamps or {}
            breaker_dict = circuit_breakers_state or {}
            closed_pos_list = list(closed_positions or [])
            orders_list = list(orders_history or [])

            payload: Dict[str, Any] = {
                "schema_version": schema_version,
                "timestamp_ms": timestamp_ms,
                "equity_usd": round(equity_usd, 2),
                "peak_equity_usd": round(peak_equity_usd, 2),
                "active_positions": pos_list,
                "closed_trades_count": closed_trades_count,
                "metrics": met_dict,
                "candle_sync_timestamps": candle_dict,
                "circuit_breakers_state": breaker_dict,
                "idempotency_keys": idemp_list,
                "closed_positions": closed_pos_list,
                "orders_history": orders_list,
            }

            raw_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            checksum = hashlib.sha256(raw_bytes).hexdigest()

            envelope = {
                "checksum_sha256": checksum,
                "data": payload,
            }

            # 1. Persist to SQLite application_checkpoints table
            if self.mode == PersistenceMode.REQUIRED_DURABLE:
                if self.db is None:
                    self._last_save_success = False
                    self._last_error = "Database instance is None in REQUIRED_DURABLE mode"
                    logger.critical("Persistence FAILURE: Database is None in REQUIRED_DURABLE mode")
                    raise PersistenceError(self._last_error)

                try:
                    with self.db.transaction():
                        self.db.execute(
                            """
                            INSERT INTO application_checkpoints (
                                checkpoint_id, schema_version, timestamp_ms, equity_usd, peak_equity_usd,
                                closed_trades_count, active_positions_json, metrics_json,
                                candle_sync_timestamps_json, circuit_breakers_state_json, idempotency_keys_json,
                                closed_positions_json, orders_history_json,
                                checksum_sha256, created_at_ts
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(checkpoint_id) DO UPDATE SET
                                schema_version = excluded.schema_version,
                                timestamp_ms = excluded.timestamp_ms,
                                equity_usd = excluded.equity_usd,
                                peak_equity_usd = excluded.peak_equity_usd,
                                closed_trades_count = excluded.closed_trades_count,
                                active_positions_json = excluded.active_positions_json,
                                metrics_json = excluded.metrics_json,
                                candle_sync_timestamps_json = excluded.candle_sync_timestamps_json,
                                circuit_breakers_state_json = excluded.circuit_breakers_state_json,
                                idempotency_keys_json = excluded.idempotency_keys_json,
                                closed_positions_json = excluded.closed_positions_json,
                                orders_history_json = excluded.orders_history_json,
                                checksum_sha256 = excluded.checksum_sha256,
                                created_at_ts = excluded.created_at_ts;
                            """,
                            (
                                "latest",
                                schema_version,
                                timestamp_ms,
                                round(equity_usd, 2),
                                round(peak_equity_usd, 2),
                                closed_trades_count,
                                json.dumps(pos_list),
                                json.dumps(met_dict),
                                json.dumps(candle_dict),
                                json.dumps(breaker_dict),
                                json.dumps(idemp_list),
                                json.dumps(closed_pos_list),
                                json.dumps(orders_list),
                                checksum,
                                time.time(),
                            )
                        )
                except Exception as db_err:
                    self._last_save_success = False
                    self._last_error = f"Database write failed: {db_err}"
                    logger.critical(f"Persistence FAILURE in REQUIRED_DURABLE mode: {db_err}", exc_info=True)
                    raise PersistenceError(f"Database write failed in REQUIRED_DURABLE mode: {db_err}") from db_err
            elif self.db is not None:
                # In FILE_ONLY_DEV mode, best-effort database write
                try:
                    with self.db.transaction():
                        self.db.execute(
                            """
                            INSERT INTO application_checkpoints (
                                checkpoint_id, schema_version, timestamp_ms, equity_usd, peak_equity_usd,
                                closed_trades_count, active_positions_json, metrics_json,
                                candle_sync_timestamps_json, circuit_breakers_state_json, idempotency_keys_json,
                                closed_positions_json, orders_history_json,
                                checksum_sha256, created_at_ts
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(checkpoint_id) DO UPDATE SET
                                schema_version = excluded.schema_version,
                                timestamp_ms = excluded.timestamp_ms,
                                equity_usd = excluded.equity_usd,
                                peak_equity_usd = excluded.peak_equity_usd,
                                closed_trades_count = excluded.closed_trades_count,
                                active_positions_json = excluded.active_positions_json,
                                metrics_json = excluded.metrics_json,
                                candle_sync_timestamps_json = excluded.candle_sync_timestamps_json,
                                circuit_breakers_state_json = excluded.circuit_breakers_state_json,
                                idempotency_keys_json = excluded.idempotency_keys_json,
                                closed_positions_json = excluded.closed_positions_json,
                                orders_history_json = excluded.orders_history_json,
                                checksum_sha256 = excluded.checksum_sha256,
                                created_at_ts = excluded.created_at_ts;
                            """,
                            (
                                "latest",
                                schema_version,
                                timestamp_ms,
                                round(equity_usd, 2),
                                round(peak_equity_usd, 2),
                                closed_trades_count,
                                json.dumps(pos_list),
                                json.dumps(met_dict),
                                json.dumps(candle_dict),
                                json.dumps(breaker_dict),
                                json.dumps(idemp_list),
                                json.dumps(closed_pos_list),
                                json.dumps(orders_list),
                                checksum,
                                time.time(),
                            )
                        )
                except Exception as db_err:
                    logger.warning(f"Development DB write failed in FILE_ONLY_DEV mode: {db_err}")

            # 2. Rotate previous file if current exists
            if self.checkpoint_file.exists():
                try:
                    self.checkpoint_file.replace(self.checkpoint_prev_file)
                except Exception:
                    pass

            # 3. Write atomic temporary file and rename
            temp_file = self.state_dir / f"checkpoint_temp_{os.getpid()}_{int(time.time()*1000)}.json"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(envelope, f, indent=2)

            temp_file.replace(self.checkpoint_file)
            self._last_save_success = True
            self._last_save_ts = timestamp_ms
            self._last_checksum = checksum
            self._last_error = None
            logger.debug(f"Platform checkpoint saved successfully. Hash: {checksum[:8]}")
            return True
        except PersistenceError:
            raise
        except Exception as e:
            self._last_save_success = False
            self._last_error = str(e)
            logger.error(f"Failed to save platform checkpoint: {e}", exc_info=True)
            if self.mode == PersistenceMode.REQUIRED_DURABLE:
                raise PersistenceError(f"Checkpoint save failed: {e}") from e
            return False

    def _verify_envelope(self, envelope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate envelope checksum against payload; returns data or None."""
        if not isinstance(envelope, dict):
            return None
        stored_checksum = envelope.get("checksum_sha256")
        data = envelope.get("data", {})
        if not stored_checksum or not isinstance(data, dict):
            return None

        raw_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        calculated_checksum = hashlib.sha256(raw_bytes).hexdigest()

        if stored_checksum != calculated_checksum:
            logger.critical(
                f"CHECKPOINT CORRUPTION DETECTED: Stored hash {stored_checksum} != "
                f"Calculated hash {calculated_checksum}."
            )
            return None
        return data

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load and verify platform checkpoint from database or disk with failover."""
        if self.mode == PersistenceMode.REQUIRED_DURABLE and self.db is None:
            raise PersistenceError("Database handle is None in REQUIRED_DURABLE mode; cannot load checkpoint safely.")

        # 1. Attempt load from SQLite database
        if self.db is not None:
            try:
                row = self.db.fetchone(
                    """
                    SELECT schema_version, timestamp_ms, equity_usd, peak_equity_usd,
                           closed_trades_count, active_positions_json, metrics_json,
                           candle_sync_timestamps_json, circuit_breakers_state_json,
                           idempotency_keys_json,
                           closed_positions_json, orders_history_json,
                           checksum_sha256
                    FROM application_checkpoints WHERE checkpoint_id = ?;
                    """,
                    ("latest",)
                )
                if row:
                    payload = {
                        "schema_version": row["schema_version"],
                        "timestamp_ms": row["timestamp_ms"],
                        "equity_usd": row["equity_usd"],
                        "peak_equity_usd": row["peak_equity_usd"],
                        "active_positions": json.loads(row["active_positions_json"]),
                        "closed_trades_count": row["closed_trades_count"],
                        "metrics": json.loads(row["metrics_json"]),
                        "candle_sync_timestamps": json.loads(row["candle_sync_timestamps_json"]),
                        "circuit_breakers_state": json.loads(row["circuit_breakers_state_json"]),
                        "idempotency_keys": json.loads(row["idempotency_keys_json"]),
                        "closed_positions": json.loads(row["closed_positions_json"]) if "closed_positions_json" in row.keys() else [],
                        "orders_history": json.loads(row["orders_history_json"]) if "orders_history_json" in row.keys() else [],
                    }
                    raw_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
                    calc_checksum = hashlib.sha256(raw_bytes).hexdigest()
                    if calc_checksum == row["checksum_sha256"]:
                        logger.info(
                            f"RESTART RECOVERY (SQL): Loaded checkpoint from {payload['timestamp_ms']} "
                            f"with {len(payload['active_positions'])} active positions. Checksum verified."
                        )
                        return payload
                    else:
                        logger.warning("Database checkpoint failed checksum validation; falling back to disk.")
            except Exception as db_err:
                logger.warning(f"Error loading checkpoint from database: {db_err}")
                if self.mode == PersistenceMode.REQUIRED_DURABLE and not self.checkpoint_file.exists() and not self.checkpoint_prev_file.exists():
                    raise PersistenceError(f"Database checkpoint load failed in REQUIRED_DURABLE mode: {db_err}") from db_err

        # 2. Attempt load from primary file
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    envelope = json.load(f)
                verified_data = self._verify_envelope(envelope)
                if verified_data is not None:
                    logger.info(
                        f"RESTART RECOVERY (File): Loaded checkpoint from {verified_data.get('timestamp_ms')} "
                        f"with {len(verified_data.get('active_positions', []))} active positions. Checksum verified."
                    )
                    return verified_data
                logger.warning("Primary checkpoint file corrupted; attempting previous backup checkpoint.")
            except Exception as ex:
                logger.warning(f"Failed to read primary checkpoint file: {ex}")

        # 3. Attempt failover to previous checkpoint
        if self.checkpoint_prev_file.exists():
            try:
                with open(self.checkpoint_prev_file, "r", encoding="utf-8") as f:
                    envelope = json.load(f)
                verified_data = self._verify_envelope(envelope)
                if verified_data is not None:
                    logger.info(
                        f"RESTART RECOVERY (Backup File): Recovered from previous checkpoint timestamp {verified_data.get('timestamp_ms')}."
                    )
                    return verified_data
            except Exception as ex:
                logger.error(f"Failed to read backup checkpoint file: {ex}")

        logger.info("No valid existing checkpoint found. Starting with pristine state.")
        return None
