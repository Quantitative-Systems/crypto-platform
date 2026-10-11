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

        if state_dir is not None:
            self.state_dir = Path(state_dir)
        elif os.environ.get("PYTEST_CURRENT_TEST") and getattr(self.db, "_is_memory", False):
            import tempfile
            self.state_dir = Path(tempfile.gettempdir()) / f"pytest_state_{os.getpid()}"
        else:
            self.state_dir = DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.state_dir / "platform_checkpoint.json"
        self.checkpoint_prev_file = self.state_dir / "platform_checkpoint_prev.json"

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

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Compute SHA-256 checksum over deterministic canonical JSON."""
        raw_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def _heal_file_from_payload(self, payload: Dict[str, Any]) -> None:
        """Heals local checkpoint file using verified payload."""
        checksum = self._calculate_checksum(payload)
        envelope = {
            "checksum_sha256": checksum,
            "data": payload,
        }
        temp_file = self.state_dir / f"checkpoint_heal_{os.getpid()}_{int(time.time()*1000)}.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2)
        temp_file.replace(self.checkpoint_file)

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
        fills_history: Optional[List[Dict[str, Any]]] = None,
        last_received_candle: Optional[Dict[str, Dict[str, int]]] = None,
        last_closed_candle: Optional[Dict[str, Dict[str, int]]] = None,
        last_processed_candle: Optional[Dict[str, Dict[str, int]]] = None,
        last_evaluated_decision_ts: Optional[Dict[str, int]] = None,
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
            fills_list = list(fills_history or [])
            recv_candle = last_received_candle or {}
            closed_candle = last_closed_candle or {}
            proc_candle = last_processed_candle or {}
            eval_dec = last_evaluated_decision_ts or {}

            candle_semantics = {
                "last_received_candle": recv_candle,
                "last_closed_candle": closed_candle,
                "last_processed_candle": proc_candle,
                "last_evaluated_decision_ts": eval_dec,
            }

            payload: Dict[str, Any] = {
                "schema_version": schema_version,
                "timestamp_ms": timestamp_ms,
                "equity_usd": round(equity_usd, 2),
                "peak_equity_usd": round(peak_equity_usd, 2),
                "active_positions": pos_list,
                "open_positions": pos_list,
                "closed_trades_count": closed_trades_count,
                "metrics": met_dict,
                "candle_sync_timestamps": candle_dict,
                "circuit_breakers_state": breaker_dict,
                "idempotency_keys": idemp_list,
                "closed_positions": closed_pos_list,
                "orders_history": orders_list,
                "fills_history": fills_list,
                "candle_semantics": candle_semantics,
                "last_received_candle": recv_candle,
                "last_closed_candle": closed_candle,
                "last_processed_candle": proc_candle,
                "last_evaluated_decision_ts": eval_dec,
            }

            checksum = self._calculate_checksum(payload)
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
                                closed_positions_json, orders_history_json, fills_history_json,
                                candle_semantics_json, checksum_sha256, created_at_ts
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                fills_history_json = excluded.fills_history_json,
                                candle_semantics_json = excluded.candle_semantics_json,
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
                                json.dumps(fills_list),
                                json.dumps(candle_semantics),
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
                                closed_positions_json, orders_history_json, fills_history_json,
                                candle_semantics_json, checksum_sha256, created_at_ts
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                fills_history_json = excluded.fills_history_json,
                                candle_semantics_json = excluded.candle_semantics_json,
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
                                json.dumps(fills_list),
                                json.dumps(candle_semantics),
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

        calculated_checksum = self._calculate_checksum(data)
        if stored_checksum != calculated_checksum:
            logger.critical(
                f"CHECKPOINT CORRUPTION DETECTED: Stored hash {stored_checksum} != "
                f"Calculated hash {calculated_checksum}."
            )
            return None
        return data

    def _load_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Reads and validates envelope from disk file."""
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            envelope = json.load(f)
        return self._verify_envelope(envelope)

    def _load_from_database(self) -> Optional[Dict[str, Any]]:
        """Queries and validates checkpoint from database."""
        if self.db is None:
            return None

        row = self.db.fetchone(
            """
            SELECT schema_version, timestamp_ms, equity_usd, peak_equity_usd,
                   closed_trades_count, active_positions_json, metrics_json,
                   candle_sync_timestamps_json, circuit_breakers_state_json,
                   idempotency_keys_json,
                   closed_positions_json, orders_history_json,
                   fills_history_json, candle_semantics_json,
                   checksum_sha256
            FROM application_checkpoints WHERE checkpoint_id = ?;
            """,
            ("latest",)
        )
        if not row:
            return None

        # Reconstruct payload dictionary
        row_keys = row.keys() if hasattr(row, "keys") else []
        closed_pos = json.loads(row["closed_positions_json"]) if "closed_positions_json" in row_keys and row["closed_positions_json"] else []
        orders_hist = json.loads(row["orders_history_json"]) if "orders_history_json" in row_keys and row["orders_history_json"] else []
        fills_hist = json.loads(row["fills_history_json"]) if "fills_history_json" in row_keys and row["fills_history_json"] else []
        c_semantics = json.loads(row["candle_semantics_json"]) if "candle_semantics_json" in row_keys and row["candle_semantics_json"] else {}

        active_positions = json.loads(row["active_positions_json"])
        payload = {
            "schema_version": row["schema_version"],
            "timestamp_ms": row["timestamp_ms"],
            "equity_usd": row["equity_usd"],
            "peak_equity_usd": row["peak_equity_usd"],
            "active_positions": active_positions,
            "open_positions": active_positions,
            "closed_trades_count": row["closed_trades_count"],
            "metrics": json.loads(row["metrics_json"]),
            "candle_sync_timestamps": json.loads(row["candle_sync_timestamps_json"]),
            "circuit_breakers_state": json.loads(row["circuit_breakers_state_json"]),
            "idempotency_keys": json.loads(row["idempotency_keys_json"]),
            "closed_positions": closed_pos,
            "orders_history": orders_hist,
            "fills_history": fills_hist,
            "candle_semantics": c_semantics,
            "last_received_candle": c_semantics.get("last_received_candle", {}),
            "last_closed_candle": c_semantics.get("last_closed_candle", {}),
            "last_processed_candle": c_semantics.get("last_processed_candle", {}),
            "last_evaluated_decision_ts": c_semantics.get("last_evaluated_decision_ts", {}),
        }

        calc_checksum = self._calculate_checksum(payload)
        stored_checksum = row["checksum_sha256"]
        if calc_checksum != stored_checksum:
            # Backward compatibility check for earlier schema versions (v1, v2, v3)
            is_valid_legacy = False
            if row["schema_version"] < 4:
                legacy_payload = {
                    "schema_version": row["schema_version"],
                    "timestamp_ms": row["timestamp_ms"],
                    "equity_usd": row["equity_usd"],
                    "peak_equity_usd": row["peak_equity_usd"],
                    "active_positions": active_positions,
                    "closed_trades_count": row["closed_trades_count"],
                    "metrics": json.loads(row["metrics_json"]),
                    "candle_sync_timestamps": json.loads(row["candle_sync_timestamps_json"]),
                    "circuit_breakers_state": json.loads(row["circuit_breakers_state_json"]),
                    "idempotency_keys": json.loads(row["idempotency_keys_json"]),
                }
                if self._calculate_checksum(legacy_payload) == stored_checksum:
                    is_valid_legacy = True
                else:
                    if "closed_positions_json" in row_keys and row["closed_positions_json"]:
                        legacy_payload["closed_positions"] = closed_pos
                    if "orders_history_json" in row_keys and row["orders_history_json"]:
                        legacy_payload["orders_history"] = orders_hist
                    if self._calculate_checksum(legacy_payload) == stored_checksum:
                        is_valid_legacy = True

            if not is_valid_legacy:
                raise PersistenceError(
                    f"Database checkpoint corruption detected: stored hash {stored_checksum} != calculated {calc_checksum}"
                )
        return payload

    def load_checkpoint(self, allow_disaster_recovery: bool = False) -> Optional[Dict[str, Any]]:
        """Load and verify platform checkpoint from database or disk with failover.
        
        Enforces:
        - In REQUIRED_DURABLE mode:
          * Normal recovery requires database checkpoint.
          * Checks for split-brain disagreement between DB and file checkpoints.
          * Corrupt DB raises PersistenceError unless allow_disaster_recovery=True.
          * Heals corrupt file checkpoint from healthy DB.
        - In FILE_ONLY_DEV mode:
          * File checkpoint is primary, with prev file fallback.
        """
        if self.mode == PersistenceMode.REQUIRED_DURABLE:
            if self.db is None:
                raise PersistenceError("Database handle is None in REQUIRED_DURABLE mode; cannot load checkpoint safely.")

            # 1. Attempt database load
            db_payload = None
            db_err: Optional[Exception] = None
            try:
                db_payload = self._load_from_database()
            except Exception as e:
                db_err = e

            # 2. Attempt file load
            file_payload = None
            if self.checkpoint_file.exists():
                try:
                    file_payload = self._load_from_file(self.checkpoint_file)
                except Exception:
                    file_payload = None

            # 3. Check for split-brain conflict when both exist
            if db_payload is not None and file_payload is not None:
                db_ts = db_payload.get("timestamp_ms", 0)
                file_ts = file_payload.get("timestamp_ms", 0)
                db_eq = db_payload.get("equity_usd", 0.0)
                file_eq = file_payload.get("equity_usd", 0.0)
                db_hash = self._calculate_checksum(db_payload)
                file_hash = self._calculate_checksum(file_payload)

                if db_hash != file_hash and (abs(db_ts - file_ts) > 1000 or abs(db_eq - file_eq) > 0.01):
                    err_msg = (
                        f"Checkpoint conflict: Database and disk checkpoints disagree! "
                        f"DB (ts={db_ts}, eq={db_eq}, hash={db_hash[:8]}) vs "
                        f"File (ts={file_ts}, eq={file_eq}, hash={file_hash[:8]}). "
                        f"Split-brain state detected."
                    )
                    logger.critical(err_msg)
                    self._last_error = err_msg
                    raise PersistenceError(err_msg)

            # 4. Handle DB corruption / failure
            if db_err is not None:
                if not allow_disaster_recovery:
                    err_msg = f"Database checkpoint corrupted or unreadable: {db_err}. Normal recovery aborted."
                    logger.critical(err_msg)
                    self._last_error = err_msg
                    raise PersistenceError(err_msg) from db_err
                else:
                    logger.warning(f"DISASTER RECOVERY PATH ENGAGED: DB failed ({db_err}), attempting filesystem recovery.")
                    if file_payload is not None:
                        file_payload["_recovery_source"] = "DISASTER_RECOVERY_DISK"
                        return file_payload
                    if self.checkpoint_prev_file.exists():
                        prev_payload = self._load_from_file(self.checkpoint_prev_file)
                        if prev_payload is not None:
                            prev_payload["_recovery_source"] = "DISASTER_RECOVERY_PREV_DISK"
                            return prev_payload
                    raise PersistenceError(f"Disaster recovery failed: no valid fallback checkpoint on disk ({db_err}).")

            # 5. Handle file corruption when DB is healthy
            if db_payload is not None and self.checkpoint_file.exists() and file_payload is None:
                logger.warning("Primary file checkpoint corrupted but database is healthy. Healing disk checkpoint from database.")
                try:
                    self._heal_file_from_payload(db_payload)
                except Exception as ex:
                    logger.warning(f"Could not heal disk checkpoint: {ex}")

            if db_payload is not None:
                return db_payload

            # 6. Database has no checkpoint
            if file_payload is not None:
                err_msg = "Database has no checkpoint but file checkpoint exists in REQUIRED_DURABLE mode. Inconsistent state."
                logger.critical(err_msg)
                raise PersistenceError(err_msg)

            # Neither DB nor file exists
            return None

        else:
            # FILE_ONLY_DEV Mode
            if self.checkpoint_file.exists():
                file_payload = self._load_from_file(self.checkpoint_file)
                if file_payload is not None:
                    return file_payload
            if self.checkpoint_prev_file.exists():
                prev_payload = self._load_from_file(self.checkpoint_prev_file)
                if prev_payload is not None:
                    return prev_payload
            if self.db is not None:
                try:
                    return self._load_from_database()
                except Exception:
                    pass
            return None

