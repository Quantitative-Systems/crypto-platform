"""Crypto Platform — Database Schema Migrations Manager.

Provides deterministic, versioned, transactional migrations:
- Tracks applied versions in `schema_migrations`
- Runs migrations inside atomic transactions
- Safe idempotency: repeatedly applying pending migrations is a no-op
- Provides inspection and reporting for operational CLI
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    version: int
    name: str
    up_sql: str
    down_sql: Optional[str] = None


# Canonical sequence of versioned migrations
MIGRATIONS: List[Migration] = [
    Migration(
        version=1,
        name="001_initial_auth_and_user_schema",
        up_sql="""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'TRADER',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at_ts REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            tenant_id TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at_ts REAL NOT NULL,
            expires_at_ts REAL NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0,
            raw_token_prefix TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_watchlists (
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            created_at_ts REAL NOT NULL,
            PRIMARY KEY (user_id, symbol)
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            pref_key TEXT NOT NULL,
            pref_value TEXT NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (user_id, pref_key)
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """,
        down_sql="""
        DROP TABLE IF EXISTS user_preferences;
        DROP TABLE IF EXISTS user_watchlists;
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS users;
        """
    ),
    Migration(
        version=2,
        name="002_application_checkpoints",
        up_sql="""
        CREATE TABLE IF NOT EXISTS application_checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL DEFAULT 2,
            timestamp_ms INTEGER NOT NULL,
            equity_usd REAL NOT NULL,
            peak_equity_usd REAL NOT NULL,
            closed_trades_count INTEGER NOT NULL,
            active_positions_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            candle_sync_timestamps_json TEXT NOT NULL,
            circuit_breakers_state_json TEXT NOT NULL,
            idempotency_keys_json TEXT NOT NULL DEFAULT '[]',
            checksum_sha256 TEXT NOT NULL,
            created_at_ts REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_checkpoints_ts ON application_checkpoints(timestamp_ms DESC);
        """,
        down_sql="""
        DROP TABLE IF EXISTS application_checkpoints;
        """
    ),
    Migration(
        version=3,
        name="003_checkpoint_history_extensions",
        up_sql="""
        ALTER TABLE application_checkpoints ADD COLUMN closed_positions_json TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE application_checkpoints ADD COLUMN orders_history_json TEXT NOT NULL DEFAULT '[]';
        """,
        down_sql=""
    ),
    Migration(
        version=4,
        name="004_checkpoint_candle_semantics_and_fills",
        up_sql="""
        ALTER TABLE application_checkpoints ADD COLUMN fills_history_json TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE application_checkpoints ADD COLUMN candle_semantics_json TEXT NOT NULL DEFAULT '{}';
        """,
        down_sql=""
    ),
]


class MigrationManager:
    """Manages applying and auditing schema migrations for DatabaseManager."""

    def __init__(self, db_manager: Any):
        self.db = db_manager
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Create schema_migrations table if absent."""
        sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at REAL NOT NULL
        );
        """
        self.db.execute(sql)

    def get_applied_versions(self) -> List[int]:
        """Return list of integer version numbers already applied."""
        rows = self.db.fetchall("SELECT version FROM schema_migrations ORDER BY version ASC;")
        return [row["version"] for row in rows]

    def apply_pending_migrations(self) -> List[int]:
        """Apply all unapplied migrations in ascending order safely under transaction locks."""
        newly_applied = []

        for m in sorted(MIGRATIONS, key=lambda x: x.version):
            with self.db.transaction():
                # Re-check under exclusive transaction lock to prevent concurrent double-application
                existing = self.db.fetchone(
                    "SELECT version FROM schema_migrations WHERE version = ?;",
                    (m.version,)
                )
                if existing:
                    continue

                logger.info(f"Applying migration {m.version}: {m.name}...")
                # Execute migration statements
                for statement in m.up_sql.strip().split(";"):
                    stmt = statement.strip()
                    if stmt:
                        self.db.execute(stmt)

                # Record migration
                self.db.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                    (m.version, m.name, time.time())
                )
                newly_applied.append(m.version)
                logger.info(f"Migration {m.version} applied successfully.")

        return newly_applied

    def run_migrations(self) -> List[int]:
        """Alias for apply_pending_migrations."""
        return self.apply_pending_migrations()

    def get_status(self) -> Dict[str, Any]:
        """Return migration status dictionary for CLI and diagnostics."""
        applied = set(self.get_applied_versions())
        pending = [m.version for m in MIGRATIONS if m.version not in applied]
        total = len(MIGRATIONS)
        return {
            "total_defined": total,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_versions": sorted(list(applied)),
            "pending_versions": pending,
            "current_version": max(applied) if applied else 0,
            "is_current": len(pending) == 0,
        }
