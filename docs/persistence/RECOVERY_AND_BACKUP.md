# Recovery and Backup Procedures

## 1. Overview

Crypto Platform employs dual-layered operational state durability:
1. **Relational Database Checkpoint Ledger**: Persisted transactionally in the `application_checkpoints` table with full schema versioning and payload SHA-256 validation.
2. **Atomic File Rotation Checkpoint**: Stored on filesystem storage with atomic file replacement (`os.replace`) and prior-version backup preservation (`platform_checkpoint_prev.json`).

---

## 2. Checkpoint Format & Versioning (Schema v2)

Operational supervisor checkpoints adhere to Schema v2:

```json
{
  "schema_version": 2,
  "timestamp_ms": 1700000000000,
  "equity_usd": 100000.0,
  "peak_equity_usd": 100000.0,
  "active_positions": [],
  "closed_trades_count": 0,
  "metrics": {
    "win_rate": 0.0,
    "net_r": 0.0,
    "total_trades": 0
  },
  "candle_sync_timestamps": {
    "BTCUSDT": 1700000000000
  },
  "circuit_breakers_state": {
    "DAILY_DRAWDOWN": "CLOSED"
  },
  "idempotency_keys": [
    "BTCUSDT:DEC_8FBC:1700000000000"
  ]
}
```

### Checkpoint Integrity Protection
- An explicit SHA-256 checksum (`checksum` column in DB and atomic disk write) ensures that partially written or corrupted checkpoint files are immediately flagged.
- If the primary checkpoint file is corrupted or unreadable, `StatePersistenceManager` automatically falls back to `platform_checkpoint_prev.json` or the relational database ledger.

---

## 3. Duplicate Order & Decision Prevention on Restart

### The Phantom Re-Entry Hazard
On process crash and restart, an autonomous trading supervisor might re-evaluate historical candles and attempt to re-submit orders for already-executed signals.

### Mitigation via Restored Idempotency Keys
1. Every order intent generates a unique idempotency key:
   `{SYMBOL}:{DECISION_ID}:{TIMESTAMP_MS}`
2. Executed keys are maintained in `IdempotencyExecutionGuard` and persisted in each periodic checkpoint (`idempotency_keys`).
3. Upon restart recovery, `AutonomousTradingSupervisor._attempt_restart_recovery()` loads all recorded idempotency keys into the active guard:
   ```python
   recovered_keys = checkpoint.get("idempotency_keys", [])
   if recovered_keys:
       self.idempotency_guard.restore_keys(recovered_keys)
   ```
4. If a replayed or re-evaluated candle attempts to submit the same order intent, `DuplicateOrderIntentError` is triggered, and the order is suppressed.

---

## 4. Backup & Restore Procedures

### Database Backup
Because SQLite WAL mode keeps transactions in write-ahead logs (`.db-wal`), creating a safe backup requires the standard SQLite online backup API or safe file copy:

```bash
# Using SQLite CLI online backup
sqlite3 data/crypto_platform.db ".backup data/backups/crypto_platform_backup_$(date +%Y%m%d_%H%M%S).db"
```

### State Checkpoint Backup
The directory `research/results/state/` contains:
- `platform_checkpoint.json`: Current validated operational state.
- `platform_checkpoint_prev.json`: Previous validated operational state.

To backup state checkpoints:
```bash
cp research/results/state/platform_checkpoint.json data/backups/
```

### Restore Procedure
1. Stop the platform supervisor:
   ```bash
   # Terminate process gracefully
   ```
2. Restore database:
   ```bash
   cp data/backups/crypto_platform_backup_XYZ.db data/crypto_platform.db
   # Remove stale WAL and SHM files
   rm -f data/crypto_platform.db-wal data/crypto_platform.db-shm
   ```
3. Verify migrations:
   ```bash
   python cli.py db-status
   ```
4. Restart supervisor:
   ```bash
   python cli.py start --mode PAPER
   ```
