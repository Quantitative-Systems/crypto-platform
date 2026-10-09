"""Crypto Platform — Database Connection & Lifecycle Manager.

Provides a thread-safe, resilient SQLite database manager with:
- WAL (Write-Ahead Logging) mode for concurrent read/write concurrency
- Foreign key enforcement
- Transactional context management with automatic commit/rollback
- In-memory support (:memory:) with connection retention for isolated testing
- Automatic directory initialization and schema bootstrapping
"""
from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "data" / "crypto_platform.db"


class DatabaseError(Exception):
    """Base exception for persistence failures."""
    pass


class DatabaseManager:
    """Thread-safe SQLite database manager for Crypto Platform."""

    _instances: Dict[str, "DatabaseManager"] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        in_memory: bool = False,
        auto_migrate: bool = True,
    ):
        if in_memory:
            self.db_path = ":memory:"
        elif db_path is not None:
            self.db_path = str(db_path) if str(db_path) == ":memory:" else str(Path(db_path).resolve())
        elif os.environ.get("CRYPTO_PLATFORM_DB_PATH"):
            env_path = os.environ["CRYPTO_PLATFORM_DB_PATH"]
            self.db_path = str(env_path) if str(env_path) == ":memory:" else str(Path(env_path).resolve())
        elif os.environ.get("PYTEST_CURRENT_TEST"):
            self.db_path = ":memory:"
        else:
            self.db_path = str(DEFAULT_DB_PATH)

        self._is_memory = (self.db_path == ":memory:")
        self._shared_memory_conn: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._conn_lock = threading.RLock()

        self._all_conns: List[sqlite3.Connection] = []

        if not self._is_memory:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            # For :memory:, hold an active connection so schema/data survives across calls
            self._shared_memory_conn = self._create_connection()

        if auto_migrate:
            self._run_migrations()

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection with WAL and foreign keys."""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode by default; transactions managed explicitly
            )
            conn.row_factory = sqlite3.Row

            cursor = conn.cursor()
            if not self._is_memory:
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.close()
            with self._conn_lock:
                self._all_conns.append(conn)
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to SQLite at {self.db_path}: {e}")
            raise DatabaseError(f"Database connection error: {e}") from e

    def get_connection(self) -> sqlite3.Connection:
        """Retrieve thread-safe connection."""
        if self._is_memory and self._shared_memory_conn is not None:
            return self._shared_memory_conn

        with self._conn_lock:
            conn = getattr(self._local, "conn", None)
            if conn is None:
                conn = self._create_connection()
                self._local.conn = conn
            return conn

    @contextlib.contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Transactional context manager enforcing atomic commit or rollback."""
        conn = self.get_connection()
        with self._conn_lock:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                yield conn
                cursor.execute("COMMIT;")
            except Exception as e:
                cursor.execute("ROLLBACK;")
                logger.warning(f"Transaction rolled back due to error: {e}")
                raise
            finally:
                cursor.close()

    def execute(self, sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> sqlite3.Cursor:
        """Execute single SQL statement."""
        conn = self.get_connection()
        with self._conn_lock:
            cursor = conn.cursor()
            try:
                if params is not None:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return cursor
            except sqlite3.Error as e:
                logger.error(f"SQL execution failure: {sql} | Error: {e}")
                raise DatabaseError(f"Query error: {e}") from e

    def executemany(self, sql: str, seq_of_params: List[Union[Tuple[Any, ...], Dict[str, Any]]]) -> sqlite3.Cursor:
        """Execute batch SQL statement."""
        conn = self.get_connection()
        with self._conn_lock:
            cursor = conn.cursor()
            try:
                cursor.executemany(sql, seq_of_params)
                return cursor
            except sqlite3.Error as e:
                logger.error(f"SQL executemany failure: {sql} | Error: {e}")
                raise DatabaseError(f"Batch query error: {e}") from e

    def fetchone(self, sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> Optional[sqlite3.Row]:
        """Fetch single row."""
        cursor = self.execute(sql, params)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    def fetchall(self, sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> List[sqlite3.Row]:
        """Fetch all rows."""
        cursor = self.execute(sql, params)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()

    def _run_migrations(self) -> None:
        """Run pending schema migrations on initialization."""
        from core.persistence.migrations import MigrationManager
        migrator = MigrationManager(self)
        migrator.apply_pending_migrations()

    def close(self) -> None:
        """Close connections and release file handles."""
        with self._conn_lock:
            for c in list(self._all_conns):
                try:
                    c.close()
                except Exception:
                    pass
            self._all_conns.clear()
            self._shared_memory_conn = None
            self._local.conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    @classmethod
    def reset_all(cls) -> None:
        """Close all cached instances and clear singleton map."""
        with cls._lock:
            for mgr in list(cls._instances.values()):
                mgr.close()
            cls._instances.clear()


def get_db_manager(
    db_path: Optional[Union[str, Path]] = None,
    in_memory: bool = False,
    force_new: bool = False,
) -> DatabaseManager:
    """Singleton-friendly factory for DatabaseManager instances."""
    if os.environ.get("PYTEST_CURRENT_TEST") and db_path is None and not os.environ.get("CRYPTO_PLATFORM_DB_PATH"):
        in_memory = True
        force_new = True

    key = ":memory:" if in_memory else (str(db_path) if db_path else os.environ.get("CRYPTO_PLATFORM_DB_PATH", str(DEFAULT_DB_PATH)))
    if force_new or in_memory:
        return DatabaseManager(db_path=db_path, in_memory=in_memory)

    with DatabaseManager._lock:
        if key not in DatabaseManager._instances:
            DatabaseManager._instances[key] = DatabaseManager(db_path=db_path, in_memory=in_memory)
        return DatabaseManager._instances[key]
