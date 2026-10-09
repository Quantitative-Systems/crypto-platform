# Database Architecture and Schema Migrations

## 1. Overview and Architecture Boundary

Crypto Platform implements durable, restart-safe relational persistence behind strict service and repository interfaces (`core.persistence.database.DatabaseManager` and `core.persistence.migrations.MigrationManager`).

### Storage Engine
- **Engine**: SQLite 3 in WAL (`Write-Ahead Logging`) mode.
- **Location**: Persistent local file path (`data/crypto_platform.db` by default, or configurable via `CRYPTO_PLATFORM_DB_PATH`).
- **Isolation / Compatibility**: Repository boundaries abstract raw database mechanics so the engine can migrate to PostgreSQL for multi-instance cloud deployments without altering business, risk, or quantitative research logic.

---

## 2. Durability Settings & Realistic Guarantees

Durability is configured via PRAGMA statements during database initialization. The platform provides configurable synchronous modes via the `CRYPTO_PLATFORM_SQLITE_SYNCHRONOUS` environment variable (`NORMAL` or `FULL`).

### PRAGMA Configuration
- `PRAGMA journal_mode = WAL;`: Enables concurrent readers alongside a writer. WAL writes append sequentially to `.db-wal`.
- `PRAGMA synchronous = NORMAL;` (Default):
  - In WAL mode with `synchronous = NORMAL`, SQLite syncs the WAL file before every checkpoint, but not on every transaction commit.
- `PRAGMA synchronous = FULL;` (Maximum Durability):
  - Every transaction commit syncs the WAL file to disk.
- `PRAGMA foreign_keys = ON;`: Enforces referential integrity at the database engine level.
- `PRAGMA busy_timeout = 5000;`: Waits up to 5,000 milliseconds on lock contention before raising `sqlite3.BusyError`.

### Realistic Durability Guarantees by Failure Scenario

| Failure Scenario | `synchronous = NORMAL` | `synchronous = FULL` | Operational Recovery Mechanism |
| :--- | :--- | :--- | :--- |
| **Process Crash** (SIGKILL, segfault, unhandled exception) | **Zero Data Loss** | **Zero Data Loss** | OS buffers remain intact; committed WAL frames are preserved and automatically replayed on next open. |
| **Host Crash / Power Failure** | **Potential loss of last uncheckpointed transactions** | **Zero Data Loss** (subject to disk write cache flush) | WAL is flushed on syncs. On boot, SQLite rolls forward uncorrupted WAL frames up to the last valid commit checksum. Incomplete writes roll back cleanly. |
| **Database File Corruption** | **Detected via checksums / PRAGMA integrity_check** | **Detected via checksums / PRAGMA integrity_check** | Checkpoint SHA-256 validation flags corruption. System fails closed and can restore from online backup (`DatabaseManager.restore_from_backup()`). |
| **Container Replacement** (Stateless container restart) | **Complete Data Loss unless backed by Persistent Volume** | **Complete Data Loss unless backed by Persistent Volume** | Containers (e.g. ECS Fargate, Kubernetes) must mount persistent EBS/EFS volumes. On ephemeral container termination, local disk state is destroyed. |
| **Persistent Volume / Disk Failure** | **Data Loss at volume level** | **Data Loss at volume level** | Mitigated by periodic online backups (`DatabaseManager.backup_to_file()`) shipped to redundant cloud storage (e.g. S3 / GCS). |

> [!IMPORTANT]
> **Honest Durability Statement**
> No storage system guarantees zero data loss under catastrophic physical hardware or unmounted ephemeral container destruction. Crypto Platform guarantees zero data loss across process crashes, and achieves point-in-time recovery across host crashes and disk corruption through SHA-256 verified checkpoints and transactional WAL replay.

---

## 3. Persistence Failure Policy & Modes

To prevent silent data degradation, `StatePersistenceManager` enforces explicit persistence modes:

1. **`PersistenceMode.REQUIRED_DURABLE` (Default & Production Required)**:
   - Database persistence is mandatory.
   - Any failure in database initialization, schema migration, or checkpoint persistence raises `PersistenceError`.
   - The platform never enters or continues an unsafe operational state if database writes fail.
   - A local JSON file write is never treated as proof of durable persistence.
   - If a checkpoint save fails, the supervisor sets `system_status = "PERSISTENCE_DEGRADED"`, trips critical alerts, and suspends new trading decisions.

2. **`PersistenceMode.FILE_ONLY_DEV` (Explicit Opt-In for Local Development)**:
   - Intended strictly for local development or disconnected exploratory testing.
   - Uses file-only storage (`platform_checkpoint.json`).
   - Requires explicit configuration (`mode=PersistenceMode.FILE_ONLY_DEV`).

---

## 4. Transaction Boundaries & Concurrency

- **Atomic Transactions**: All mutations execute inside explicit transactions managed via `with db.transaction():`.
- **Immediate Write Locking**: Transactions issue `BEGIN IMMEDIATE;` to acquire write locks upfront, eliminating `SQLITE_BUSY` deadlock cycles during concurrent multi-step operations.
- **Fail-Safe Rollback**: Any unhandled exception triggers an immediate `ROLLBACK;`, preventing corrupted partial states from being committed.
- **Thread Safety**: Connections are isolated per-thread using thread-local storage (`threading.local`) and tracked within `DatabaseManager` using a re-entrant lock (`threading.RLock`).

---

## 5. Schema Versioning & Migrations

Migrations are versioned sequentially and tracked in the `schema_migrations` table:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at REAL NOT NULL
);
```

### Concurrent Migration Protection
To guarantee that two processes starting simultaneously cannot apply the same migration twice due to stale read snapshots, `MigrationManager` executes migrations inside an exclusive transaction (`BEGIN IMMEDIATE;`) and re-queries `schema_migrations` within the transaction immediately before applying any migration script.

### Applied Migrations:

#### Migration 1: `001_initial_auth_and_user_schema`
Creates user identity, session management, and preference tables:
- `users`: User identity, hashed passwords, salts, role-based access control, active status.
- `sessions`: Cryptographic session tokens (hashed via SHA-256), expiration timestamps, revocation flags.
- `user_watchlists`: Multi-tenant symbol watchlists with cascade deletion.
- `user_preferences`: Arbitrary user setting key-value pairs.

#### Migration 2: `002_application_checkpoints`
Creates durable state checkpoints for operational supervisor restarts:
- `application_checkpoints`: Stores checkpoint payload JSON, schema version, timestamp, equity, peak equity, active positions count, and SHA-256 payload checksums.
- Indices: `idx_checkpoints_ts` on `timestamp_ms DESC` for O(1) recovery queries.

#### Migration 3: `003_checkpoint_history_extensions`
Extends `application_checkpoints` to support complete operational history:
- `closed_positions_json`: TEXT column storing JSON array of fully closed positions.
- `orders_history_json`: TEXT column storing JSON array of recent order records.

---

## 6. Online Backup and Restore API

Crypto Platform integrates SQLite's native online backup API (`sqlite3.Connection.backup()`), ensuring non-blocking, consistent live backups without locking active readers:

### Python API
```python
# Create live consistent backup
db_manager.backup_to_file("data/backups/crypto_platform_backup.db")

# Restore database from backup
db_manager.restore_from_backup("data/backups/crypto_platform_backup.db")
```

### CLI Commands
```bash
# Inspect migration status
python cli.py db-status [--db-path /path/to/db]

# Apply pending migrations
python cli.py db-migrate [--db-path /path/to/db]
```

---

## 7. Duplicate Order & Decision Prevention on Restart

1. **Idempotency Execution Guard**: Order intent execution keys (`{SYMBOL}:{DECISION_ID}:{TIMESTAMP_MS}`) are saved in the checkpoint and restored into `IdempotencyExecutionGuard` during supervisor boot.
2. **Replayed Candle Suppression**: If historical candles are re-evaluated upon boot, duplicate order intents match existing idempotency keys and are rejected with `DuplicateOrderIntentError`.
3. **Ledger Reconciliation**: Restored positions are reconciled against the authoritative ledger prior to processing any new decisions. If any mismatch or inconsistency is found, the system halts with `RECOVERY_FAILED_HALTED`.

