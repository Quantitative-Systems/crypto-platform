# Database Architecture and Schema Migrations

## 1. Overview and Architecture Boundary

Crypto Platform implements durable, restart-safe relational persistence behind strict service and repository interfaces (`core.persistence.database.DatabaseManager` and `core.persistence.migrations.MigrationManager`).

### Storage Engine
- **Engine**: SQLite 3 in WAL (`Write-Ahead Logging`) mode.
- **Location**: Persistent local file path (`data/crypto_platform.db` by default, or configurable via `CRYPTO_PLATFORM_DB_PATH`).
- **Isolation / Compatibility**: Repository boundaries abstract raw database mechanics so the engine can migrate to PostgreSQL for multi-instance cloud deployments without altering business, risk, or quantitative research logic.

> [!WARNING]
> **Ephemeral Container Storage Limitation**
> Local SQLite with WAL mode is durable only when the backing storage is non-ephemeral (e.g., persistent volumes, mounted state disks). If deployed inside a stateless container (e.g., AWS ECS Fargate, GCP Cloud Run) without persistent volume mounts, local SQLite storage is destroyed upon task recycling. For multi-instance horizontal scaling, transition to managed PostgreSQL (`PostgresDatabaseManager`) using the existing repository abstraction.

---

## 2. Database Ownership & Connection Lifecycle

- **Thread-Safe Connection Management**: Handled via `DatabaseManager`, which manages thread-local connections and tracks active file descriptors with a re-entrant lock (`threading.RLock`).
- **PRAGMA Settings**:
  - `PRAGMA journal_mode = WAL;`: Enables concurrent readers alongside a writer.
  - `PRAGMA synchronous = NORMAL;`: Ensures durability across OS crashes while maximizing throughput.
  - `PRAGMA foreign_keys = ON;`: Enforces referential integrity at the database engine level.
  - `PRAGMA busy_timeout = 5000;`: Waits up to 5,000 milliseconds on lock contention before raising `sqlite3.BusyError`.

---

## 3. Transaction Boundaries & Concurrency

- **Atomic Transactions**: All mutations execute inside explicit transactions managed via `with db.transaction():`.
- **Immediate Write Locking**: Transactions issue `BEGIN IMMEDIATE;` to acquire write locks upfront, eliminating `SQLITE_BUSY` deadlock cycles during concurrent multi-step operations.
- **Fail-Safe Rollback**: Any unhandled exception triggers an immediate `ROLLBACK;`, preventing corrupted partial states from being committed.

---

## 4. Schema Versioning & Migrations

Migrations are versioned sequentially and tracked in the `schema_migrations` table:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at REAL NOT NULL
);
```

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

---

## 5. Migration CLI Commands

Database migrations are managed via the unified platform CLI:

### Inspect Migration Status
```bash
python cli.py db-status [--db-path /path/to/db]
```
Example Output:
```
Database: C:\Users\nares\Workspace\crypto-platform\data\crypto_platform.db
Current version: 2
Applied migrations: [1, 2]
Pending migrations: []
```

### Apply Pending Migrations
```bash
python cli.py db-migrate [--db-path /path/to/db]
```
Example Output:
```
Applying database migrations to: C:\Users\nares\Workspace\crypto-platform\data\crypto_platform.db...
Migrations applied successfully: []
Current version: 2, pending: 0
```

---

## 6. Recovery After Interrupted Writes & Duplicate Prevention

1. **Write-Ahead Log Recovery**: Interrupted writes or power outages are automatically repaired by SQLite's WAL replay on the next connection open.
2. **Idempotency Guard**: Order intent execution keys (`{SYMBOL}:{DECISION_ID}:{TIMESTAMP_MS}`) are saved in the checkpoint and restored into `IdempotencyExecutionGuard` during supervisor boot, preventing duplicate order routing across restarts.
3. **Migration Idempotency**: Migration scripts are guarded by checking `schema_migrations`; re-running migrations is completely idempotent and safe.
