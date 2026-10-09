"""Crypto Platform — Persistence Package.

Provides durable, restart-safe SQLite and file persistence with:
- DatabaseManager (WAL mode, thread-safe, transactional)
- MigrationManager (versioned, atomic schema migrations)
"""
from core.persistence.database import DatabaseError, DatabaseManager, get_db_manager
from core.persistence.migrations import Migration, MigrationManager

__all__ = [
    "DatabaseError",
    "DatabaseManager",
    "Migration",
    "MigrationManager",
    "get_db_manager",
]
