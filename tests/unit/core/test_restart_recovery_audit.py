"""Phase 1.1 — Comprehensive Persistence and Restart-Recovery Correction Tests.

Verifies:
1. Real subprocess-level process restart recovery (Process 1 -> terminate -> Process 2).
2. Session validity and user persistence across separate Python subprocesses.
3. Checkpoint integrity, equity, active position, and idempotency key restoration across processes.
4. Duplicate order intent prevention across subprocess restarts.
5. REQUIRED_DURABLE mode fail-closed behavior when database is unavailable.
6. REQUIRED_DURABLE mode fail-closed behavior on database write failure.
7. Corrupted checkpoint fail-safe rejection (untrusted corrupted state rejected).
8. Inconsistent restored state rejection (fail-closed halt).
9. Concurrent schema migrations race condition prevention (BEGIN IMMEDIATE locking).
10. Online SQLite backup and restore verification.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.auth.auth_service import AuthService, UserRole
from core.persistence.database import DatabaseError, DatabaseManager
from core.persistence.migrations import MigrationManager
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.position.position_lifecycle import Position, PositionState
from execution.precision_engine import DuplicateOrderIntentError, IdempotencyExecutionGuard
from execution.state.state_persistence import (
    PersistenceError,
    PersistenceMode,
    StatePersistenceManager,
)


@pytest.fixture(autouse=True)
def cleanup_databases():
    """Ensure all open database instances are reset after every test."""
    yield
    DatabaseManager.reset_all()


def test_subprocess_level_restart_recovery_and_idempotency():
    """Starts Process 1, creates user and checkpoint, terminates it, and starts Process 2 to verify recovery."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "subprocess_test.db"
        state_dir = Path(tmp_dir) / "state"
        meta_file = Path(tmp_dir) / "run_meta.json"

        # --- SUBPROCESS 1: Setup User, Session, and Checkpoint ---
        sub_script_1 = f"""
import sys, json, os, time
from pathlib import Path

sys.path.insert(0, r"{os.getcwd()}")
from core.auth.auth_service import AuthService, UserRole
from execution.state.state_persistence import StatePersistenceManager, PersistenceMode

db_file = Path(r"{db_file}")
state_dir = Path(r"{state_dir}")

auth = AuthService(db_path=db_file)
user = auth.register_user(
    email="subprocess_trader@strata.internal",
    password="SubprocessSecurePassword2026!",
    role=UserRole.TRADER,
)
session = auth.authenticate("subprocess_trader@strata.internal", "SubprocessSecurePassword2026!")

pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
active_pos = [{{
    "position_id": "POS_SUB_01",
    "symbol": "BTCUSDT",
    "direction": 1,
    "entry_price": 64000.0,
    "initial_stop": 61000.0,
    "current_stop": 61000.0,
    "target_price": 76000.0,
    "size": 0.5,
    "initial_risk_dollars": 1500.0,
    "allocated_risk_pct": 0.01,
    "state": "OPEN",
}}]
idemp_keys = ["BTCUSDT:DEC_SUB_ALPHA:1700000000000"]
breakers = {{"MAX_DRAWDOWN": {{"status": "ARMED", "is_safe": True}}}}

pm.save_checkpoint(
    equity_usd=125000.0,
    peak_equity_usd=130000.0,
    active_positions=active_pos,
    closed_trades_count=5,
    metrics={{"win_rate": 0.8, "net_r": 12.5}},
    candle_sync_timestamps={{"BTCUSDT": 1700000000000}},
    circuit_breakers_state=breakers,
    idempotency_keys=idemp_keys,
)

with open(r"{meta_file}", "w") as f:
    json.dump({{
        "user_id": user.user_id,
        "token": session.token,
        "idemp_key": idemp_keys[0],
    }}, f)

auth.close()
pm.close()
sys.exit(0)
"""
        proc1 = subprocess.run([sys.executable, "-c", sub_script_1], capture_output=True, text=True)
        assert proc1.returncode == 0, f"Process 1 failed: {proc1.stderr}\nOutput: {proc1.stdout}"
        assert meta_file.exists()

        with open(meta_file, "r") as f:
            meta = json.load(f)

        token = meta["token"]
        expected_user_id = meta["user_id"]
        expected_idemp_key = meta["idemp_key"]

        # --- SUBPROCESS 2: Validate Session, Checkpoint & Idempotency Guard in Fresh Process ---
        sub_script_2 = f"""
import sys, json, os
from pathlib import Path

sys.path.insert(0, r"{os.getcwd()}")
from core.auth.auth_service import AuthService
from execution.state.state_persistence import StatePersistenceManager, PersistenceMode
from execution.precision_engine import IdempotencyExecutionGuard, DuplicateOrderIntentError

db_file = Path(r"{db_file}")
state_dir = Path(r"{state_dir}")

auth = AuthService(db_path=db_file)
val_user = auth.validate_session("{token}")
if not val_user or val_user.user_id != "{expected_user_id}":
    print("SESSION_VALIDATION_FAILED")
    sys.exit(2)

pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
checkpoint = pm.load_checkpoint()
if not checkpoint:
    print("CHECKPOINT_LOAD_FAILED")
    sys.exit(3)

if checkpoint["equity_usd"] != 125000.0:
    print(f"EQUITY_MISMATCH: {{checkpoint['equity_usd']}}")
    sys.exit(4)

if len(checkpoint["active_positions"]) != 1 or checkpoint["active_positions"][0]["position_id"] != "POS_SUB_01":
    print(f"POSITION_MISMATCH: {{checkpoint['active_positions']}}")
    sys.exit(5)

guard = IdempotencyExecutionGuard()
guard.restore_keys(checkpoint["idempotency_keys"])

# Verify that the restored key prevents duplicate order submission
try:
    guard.assert_idempotent("BTCUSDT", "DEC_SUB_ALPHA", 1700000000000)
    print("IDEMPOTENCY_BREACH: Duplicate order was not rejected!")
    sys.exit(6)
except DuplicateOrderIntentError:
    pass

# Verify that a new key succeeds
new_key = guard.assert_idempotent("BTCUSDT", "DEC_SUB_BETA", 1700000005000)
if not new_key:
    sys.exit(7)

auth.close()
pm.close()
print("SUBPROCESS_2_SUCCESS")
sys.exit(0)
"""
        proc2 = subprocess.run([sys.executable, "-c", sub_script_2], capture_output=True, text=True)
        assert proc2.returncode == 0, f"Process 2 failed: {proc2.stderr}\nOutput: {proc2.stdout}"
        assert "SUBPROCESS_2_SUCCESS" in proc2.stdout


def test_required_durable_mode_fails_closed_when_database_unavailable():
    """In REQUIRED_DURABLE mode, an unavailable database must raise PersistenceError, not fall back silently."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Use an invalid file path that cannot be written
        invalid_path = Path(tmp_dir) / "non_existent_subdir" / "unwritable" / "db.sqlite"
        # Make parent a file to force an OS filesystem error
        blocker = Path(tmp_dir) / "non_existent_subdir"
        blocker.write_text("blocker_file")

        with pytest.raises(PersistenceError, match="Durable persistence is required but database is unavailable"):
            StatePersistenceManager(db_path=invalid_path, mode=PersistenceMode.REQUIRED_DURABLE)


def test_required_durable_mode_fails_closed_on_write_failure():
    """In REQUIRED_DURABLE mode, a database write failure must raise PersistenceError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "write_fail_test.db"
        pm = StatePersistenceManager(db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        orig_db = pm.db

        try:
            # Mock db transaction to raise DatabaseError
            mock_db = MagicMock()
            mock_db.transaction.side_effect = DatabaseError("Simulated database disk I/O failure")
            pm.db = mock_db

            with pytest.raises(PersistenceError, match="Database write failed in REQUIRED_DURABLE mode"):
                pm.save_checkpoint(equity_usd=100000.0, peak_equity_usd=100000.0)

            # Persistence health must reflect degradation
            health = pm.get_persistence_health()
            assert health["status"] == "DEGRADED"
            assert health["last_save_success"] is False
            assert "Simulated database disk I/O failure" in health["last_error"]
        finally:
            if orig_db:
                orig_db.close()
            DatabaseManager.reset_all()


def test_corrupted_checkpoint_fails_closed():
    """Corrupted checkpoint data with mismatched SHA-256 hash must be rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "corrupt_test.db"
        state_dir = Path(tmp_dir) / "checkpoints"
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)

        pm.save_checkpoint(equity_usd=100000.0, peak_equity_usd=100000.0)

        # Corrupt DB checksum
        pm.db.execute("UPDATE application_checkpoints SET checksum_sha256 = 'CORRUPTED_HASH';")

        # Corrupt disk file
        json_file = state_dir / "platform_checkpoint.json"
        if json_file.exists():
            with open(json_file, "r") as f:
                data = json.load(f)
            data["checksum_sha256"] = "CORRUPTED_FILE_HASH"
            with open(json_file, "w") as f:
                json.dump(data, f)

        # Loading must return None and log critical corruption
        loaded = pm.load_checkpoint()
        assert loaded is None
        pm.close()


def test_supervisor_aborts_recovery_on_inconsistent_checkpoint():
    """Supervisor _attempt_restart_recovery must abort and halt fail-closed on invalid checkpoint data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "inconsistent_test.db"
        state_dir = Path(tmp_dir) / "checkpoints"
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)

        # Save an inconsistent checkpoint with negative equity
        pm.save_checkpoint(
            equity_usd=-50000.0,  # Inconsistent / corrupt equity
            peak_equity_usd=100000.0,
        )

        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"])
        supervisor.state_persistence = pm

        supervisor._attempt_restart_recovery()
        assert supervisor.system_status == "RECOVERY_FAILED_HALTED"

        # Attempting to start in halted state must raise RuntimeError
        with pytest.raises(RuntimeError, match="RECOVERY_FAILED_HALTED"):
            import asyncio
            asyncio.run(supervisor.start())

        pm.close()


def test_concurrent_schema_migrations():
    """Simulates multiple threads applying migrations concurrently to ensure no race conditions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "concurrent_mig.db"
        db_mgr = DatabaseManager(db_file, auto_migrate=False)

        errors = []

        def worker():
            try:
                migrator = MigrationManager(db_mgr)
                migrator.apply_pending_migrations()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent migrations produced errors: {errors}"

        status = MigrationManager(db_mgr).get_status()
        assert status["is_current"] is True
        assert status["current_version"] == 3
        db_mgr.close()


def test_online_database_backup_and_restore():
    """Tests SQLite online backup and restore via DatabaseManager."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_db_file = Path(tmp_dir) / "source.db"
        backup_file = Path(tmp_dir) / "backup.db"
        restored_db_file = Path(tmp_dir) / "restored.db"

        # 1. Populate source database
        auth_src = AuthService(db_path=src_db_file)
        user = auth_src.register_user("backup_test@strata.internal", "Pass123456!", UserRole.TRADER)
        session = auth_src.authenticate("backup_test@strata.internal", "Pass123456!")
        token = session.token

        # 2. Perform online backup
        auth_src.db.backup_to_file(backup_file)
        assert backup_file.exists()
        auth_src.close()

        # 3. Restore to fresh target
        restored_mgr = DatabaseManager.restore_from_backup(backup_file, restored_db_file)
        assert restored_db_file.exists()

        # 4. Connect AuthService to restored database and verify user & session
        auth_restored = AuthService(db_manager=restored_mgr)
        valid_user = auth_restored.validate_session(token)
        assert valid_user is not None
        assert valid_user.user_id == user.user_id
        assert valid_user.email == "backup_test@strata.internal"

        auth_restored.close()
        restored_mgr.close()
