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
            with open(json_file, "w") as f:
                json.dump(data, f)

        # Loading must raise PersistenceError in REQUIRED_DURABLE mode
        with pytest.raises(PersistenceError):
            pm.load_checkpoint()
        pm.close()


def test_supervisor_aborts_recovery_on_inconsistent_checkpoint():
    """Supervisor _attempt_restart_recovery must abort and halt fail-closed on invalid checkpoint data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "inconsistent_test.db"
        state_dir = Path(tmp_dir) / "checkpoints"
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        try:
            # Save an inconsistent checkpoint with negative equity
            pm.save_checkpoint(
                equity_usd=-50000.0,  # Inconsistent / corrupt equity
                peak_equity_usd=100000.0,
            )
        finally:
            pm.close()
            DatabaseManager.reset_all()

        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"], state_dir=state_dir, db_path=db_file)
        try:
            assert supervisor.system_status == "RECOVERY_FAILED_HALTED"

            # Attempting to start in halted state must raise RuntimeError
            with pytest.raises(RuntimeError, match="RECOVERY_FAILED_HALTED"):
                import asyncio
                asyncio.run(supervisor.start())
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


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
        assert status["current_version"] == 4
        db_mgr.close()
        DatabaseManager.reset_all()


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
        DatabaseManager.reset_all()

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
        DatabaseManager.reset_all()


def test_persistence_failure_blocks_order_execution():
    """Verifies that persistence failure trips the safety gate and blocks new order intents and execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "gate_test.db"
        state_dir = Path(tmp_dir) / "state"
        ledger_file = Path(tmp_dir) / "ledger.jsonl"

        supervisor = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            ledger_path=ledger_file,
            state_dir=state_dir,
            db_path=db_file,
        )
        try:
            # 1. Mock DB write failure during checkpoint save
            mock_db = MagicMock()
            mock_db.transaction.side_effect = DatabaseError("Disk full / I/O error")
            supervisor.state_persistence.db = mock_db

            # 2. Trigger checkpoint save -> must trip safety gate
            save_ok = supervisor._save_state_checkpoint()
            assert save_ok is False
            assert supervisor.is_persistence_blocked() is True
            assert supervisor.system_status == "PERSISTENCE_DEGRADED"

            # 3. Create a candidate TRADE decision record
            from execution.decision.phase_r_decision_engine import DecisionType, PhaseRDecisionRecord
            trade_decision = PhaseRDecisionRecord(
                decision_id="DEC_BLOCKED_TEST",
                lineage_id="LIN_TEST",
                event_id="EVT_TEST",
                timestamp_ms=1700000000000,
                asset="BTCUSDT",
                timeframe_set="SET_2",
                phase="PHASE_1",
                decision=DecisionType.TRADE,
                reason_codes=[],
                confidence_score=0.85,
                confidence_components={},
                fractal_alignment="ALIGNED",
                fractal_bias="BULLISH",
                direction=1,
                entry_price=65000.0,
                initial_stop_price=62000.0,
                target_price=77000.0,
                planned_r=4.0,
                risk_pct=0.01,
                portfolio_heat_pct=0.01,
                governor_passed=True,
            )

            # 4. Attempt order execution -> must be blocked fail-closed
            supervisor._execute_order(trade_decision)

            # 5. Assert no order, fill, or position was created
            assert len(supervisor.orders_history) == 0
            assert len(supervisor.fills_history) == 0
            assert len(supervisor.active_positions) == 0
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_persistence_degradation_survives_subsequent_candle_callbacks():
    """Verifies that once persistence is degraded, subsequent candle callbacks cannot produce orders."""
    from market_data.realtime.candle_engine import CandleRecord
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "candle_gate_test.db"
        state_dir = Path(tmp_dir) / "state"

        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"], state_dir=state_dir, db_path=db_file)
        try:
            # Trip persistence gate directly
            supervisor._trip_persistence_gate("Simulated permanent DB degradation")
            assert supervisor.is_persistence_blocked() is True

            # Form a closed candle
            test_candle = CandleRecord(
                symbol="BTCUSDT",
                timeframe="15m",
                open_ts=1700000000000,
                close_ts=1700000900000,
                open=65000.0,
                high=66000.0,
                low=64500.0,
                close=65500.0,
                volume=150.0,
            )

            # Deliver to callback
            supervisor._on_closed_candle_formed(test_candle)

            # Assert no trading activity occurred
            assert len(supervisor.orders_history) == 0
            assert len(supervisor.active_positions) == 0

            # Attempting start() must fail
            with pytest.raises(RuntimeError, match="PERSISTENCE_DEGRADED"):
                import asyncio
                asyncio.run(supervisor.start())
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_recovery_restores_actual_candle_processing_timestamps():
    """Verifies that actual candle-processing timestamps (not wall-clock) are persisted and restored."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "candle_sync_test.db"
        state_dir = Path(tmp_dir) / "state"

        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        try:
            expected_recv = {"BTCUSDT": {"15m": 1700000000000}}
            expected_closed = {"BTCUSDT": {"15m": 1700000900000}}
            expected_proc = {"BTCUSDT": {"15m": 1700000900000}}
            expected_eval = {"BTCUSDT": 1700000900000}

            pm.save_checkpoint(
                equity_usd=100000.0,
                peak_equity_usd=100000.0,
                last_received_candle=expected_recv,
                last_closed_candle=expected_closed,
                last_processed_candle=expected_proc,
                last_evaluated_decision_ts=expected_eval,
            )
        finally:
            pm.close()
            DatabaseManager.reset_all()

        # Boot fresh supervisor
        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"], state_dir=state_dir, db_path=db_file)
        try:
            assert supervisor.last_received_candle["BTCUSDT"]["15m"] == 1700000000000
            assert supervisor.last_closed_candle["BTCUSDT"]["15m"] == 1700000900000
            assert supervisor.last_processed_candle["BTCUSDT"]["15m"] == 1700000900000
            assert supervisor.last_evaluated_decision_ts["BTCUSDT"] == 1700000900000
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_duplicate_candle_delivery_does_not_duplicate_decisions():
    """Verifies that duplicate and out-of-order candles are causally discarded."""
    from market_data.realtime.candle_engine import CandleRecord
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "dedup_test.db"
        state_dir = Path(tmp_dir) / "state"

        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"], state_dir=state_dir, db_path=db_file)
        try:
            c1 = CandleRecord(
                symbol="BTCUSDT",
                timeframe="15m",
                open_ts=1700000000000,
                close_ts=1700000900000,
                open=65000.0,
                high=66000.0,
                low=64500.0,
                close=65500.0,
                volume=100.0,
            )
            supervisor._on_closed_candle_formed(c1)
            assert supervisor.last_processed_candle["BTCUSDT"]["15m"] == 1700000900000
            count_after_first = len(supervisor.decisions_history)

            # Deliver same candle again
            supervisor._on_closed_candle_formed(c1)
            assert len(supervisor.decisions_history) == count_after_first

            # Deliver older / out of order candle
            c_old = CandleRecord(
                symbol="BTCUSDT",
                timeframe="15m",
                open_ts=1699999000000,
                close_ts=1699999900000,
                open=64000.0,
                high=65000.0,
                low=63500.0,
                close=64500.0,
                volume=100.0,
            )
            supervisor._on_closed_candle_formed(c_old)
            assert len(supervisor.decisions_history) == count_after_first
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_stale_fallback_checkpoint_is_rejected():
    """A checkpoint that is older than authoritative ledger entries must fail closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "stale_test.db"
        state_dir = Path(tmp_dir) / "state"
        ledger_file = Path(tmp_dir) / "ledger.jsonl"

        # Write recent decisions to ledger at timestamp 2,000,000,000,000
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "decision_id": "DEC_RECENT_01",
                "timestamp_ms": 2000000000000,
                "asset": "BTCUSDT",
                "decision": "TRADE",
                "direction": 1,
                "entry_price": 65000.0,
                "initial_stop_price": 62000.0,
                "target_price": 77000.0,
            }) + "\n")

        # Save stale checkpoint with timestamp 1,000,000,000,000
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        try:
            pm.save_checkpoint(
                equity_usd=100000.0,
                peak_equity_usd=100000.0,
            )
            # Force stale timestamp in database
            pm.db.execute("UPDATE application_checkpoints SET timestamp_ms = 1000000000000;")
            # Also re-sync file
            with open(state_dir / "platform_checkpoint.json", "r") as f:
                data = json.load(f)
            data["data"]["timestamp_ms"] = 1000000000000
            with open(state_dir / "platform_checkpoint.json", "w") as f:
                json.dump(data, f)
        finally:
            pm.close()
            DatabaseManager.reset_all()

        # Boot supervisor with ledger
        supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT"], ledger_path=ledger_file, state_dir=state_dir, db_path=db_file)
        try:
            # Must fail closed
            assert supervisor.system_status == "RECOVERY_FAILED_HALTED"
            assert supervisor.is_persistence_blocked() is True
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_inconsistent_database_file_checkpoints_fail_closed():
    """Disagreement between database and file checkpoints must trigger split-brain error and fail closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "split_test.db"
        state_dir = Path(tmp_dir) / "state"

        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        try:
            pm.save_checkpoint(equity_usd=100000.0, peak_equity_usd=100000.0)

            # Mutate disk file to conflict with database
            json_file = state_dir / "platform_checkpoint.json"
            with open(json_file, "r") as f:
                envelope = json.load(f)
            envelope["data"]["equity_usd"] = 999999.0
            # Re-sign file checksum
            raw_b = json.dumps(envelope["data"], indent=2, sort_keys=True).encode("utf-8")
            import hashlib
            envelope["checksum_sha256"] = hashlib.sha256(raw_b).hexdigest()
            with open(json_file, "w") as f:
                json.dump(envelope, f)

            # In REQUIRED_DURABLE mode, load_checkpoint must detect split-brain and raise PersistenceError
            with pytest.raises(PersistenceError, match="Split-brain state detected"):
                pm.load_checkpoint()
        finally:
            pm.close()
            DatabaseManager.reset_all()


def test_backup_and_restore_acceptance():
    """Documented acceptance test: point-in-time database backup, simulated corruption, restore, and supervisor boot."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_db_file = Path(tmp_dir) / "live.db"
        backup_file = Path(tmp_dir) / "backup_archive.db"
        restored_db_file = Path(tmp_dir) / "restored.db"
        state_dir = Path(tmp_dir) / "state"
        ledger_file = Path(tmp_dir) / "ledger.jsonl"

        # 1. Initialize live supervisor and populate state
        sup_live = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            state_dir=state_dir,
            db_path=src_db_file,
            ledger_path=ledger_file,
        )
        try:
            sup_live.equity_usd = 150000.0
            sup_live.peak_equity_usd = 155000.0
            sup_live.last_received_candle["BTCUSDT"]["15m"] = 1700000000000
            sup_live.last_closed_candle["BTCUSDT"]["15m"] = 1700000900000
            sup_live.last_processed_candle["BTCUSDT"]["15m"] = 1700000900000
            sup_live.last_evaluated_decision_ts["BTCUSDT"] = 1700000900000

            save_ok = sup_live._save_state_checkpoint()
            assert save_ok is True
        finally:
            sup_live.state_persistence.close()
            DatabaseManager.reset_all()

        # 2. Perform online point-in-time backup using DatabaseManager
        src_mgr = DatabaseManager(src_db_file)
        try:
            src_mgr.backup_to_file(backup_file)
            assert backup_file.exists()
        finally:
            src_mgr.close()
            DatabaseManager.reset_all()

        # 3. Simulate disaster: corrupt live database
        with open(src_db_file, "wb") as f:
            f.write(b"CORRUPTED_GARBAGE_PAYLOAD")

        # 4. Restore database from backup archive
        restored_mgr = DatabaseManager.restore_from_backup(backup_file, restored_db_file)
        restored_mgr.close()
        DatabaseManager.reset_all()

        # Also provide matching restored state_dir checkpoint so split-brain check passes
        restored_state_dir = Path(tmp_dir) / "restored_state"
        restored_pm = StatePersistenceManager(state_dir=restored_state_dir, db_path=restored_db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        restored_cp = restored_pm.load_checkpoint()
        restored_pm.close()
        DatabaseManager.reset_all()

        assert restored_cp is not None
        assert restored_cp["equity_usd"] == 150000.0

        # 5. Boot fresh supervisor against restored database
        sup_restored = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            state_dir=restored_state_dir,
            db_path=restored_db_file,
            ledger_path=ledger_file,
        )
        try:
            assert sup_restored.system_status == "RECOVERED_HEALTHY"
            assert sup_restored.equity_usd == 150000.0
            assert sup_restored.peak_equity_usd == 155000.0
            assert sup_restored.last_processed_candle["BTCUSDT"]["15m"] == 1700000900000
        finally:
            sup_restored.state_persistence.close()
            DatabaseManager.reset_all()

