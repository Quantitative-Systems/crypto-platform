"""Unit tests for 24/7 Recovery Watchdog, heartbeat timeout, and startup reconciliation."""
import json
import time
from pathlib import Path
import pytest
from execution.safety.watchdog import RecoveryWatchdog


def test_watchdog_heartbeat_and_liveness():
    wd = RecoveryWatchdog(heartbeat_timeout_seconds=0.5)
    wd.record_heartbeat()
    healthy, err = wd.check_liveness()
    assert healthy is True
    assert err is None

    # Sleep to simulate process stall
    time.sleep(0.6)
    healthy, err = wd.check_liveness()
    assert healthy is False
    assert "heartbeat expired" in err.lower()
    assert wd.status.safe_mode_active is True


def test_watchdog_startup_reconciliation_success():
    wd = RecoveryWatchdog()
    internal = [
        {"symbol": "BTCUSDT", "quantity": 0.5, "entry_price": 50000.0},
        {"symbol": "ETHUSDT", "quantity": 2.0, "entry_price": 3000.0},
    ]
    broker = [
        {"symbol": "BTCUSDT", "quantity": 0.5, "price": 50000.0},
        {"symbol": "ETHUSDT", "quantity": 2.0, "price": 3000.0},
    ]
    ok, err = wd.verify_startup_reconciliation(internal, broker)
    assert ok is True
    assert err is None
    assert wd.status.startup_reconciled is True
    assert wd.status.safe_mode_active is False


def test_watchdog_startup_reconciliation_orphan_broker_position():
    wd = RecoveryWatchdog()
    internal = [
        {"symbol": "BTCUSDT", "quantity": 0.5},
    ]
    broker = [
        {"symbol": "BTCUSDT", "quantity": 0.5},
        {"symbol": "SOLUSDT", "quantity": 10.0},  # Orphan in broker!
    ]
    ok, err = wd.verify_startup_reconciliation(internal, broker)
    assert ok is False
    assert "orphan broker positions" in err.lower()
    assert wd.status.safe_mode_active is True


def test_watchdog_startup_reconciliation_ghost_internal_position():
    wd = RecoveryWatchdog()
    internal = [
        {"symbol": "BTCUSDT", "quantity": 0.5},
        {"symbol": "ADAUSDT", "quantity": 1000.0},  # Missing from broker!
    ]
    broker = [
        {"symbol": "BTCUSDT", "quantity": 0.5},
    ]
    ok, err = wd.verify_startup_reconciliation(internal, broker)
    assert ok is False
    assert "ghost internal positions" in err.lower()
    assert wd.status.safe_mode_active is True


def test_watchdog_checkpoint_integrity(tmp_path: Path):
    wd = RecoveryWatchdog(checkpoint_dir=str(tmp_path))
    state = {"positions": {"BTCUSDT": 0.5}, "capital": 10000.0, "mode": "PAPER"}

    # Save
    chk_path = wd.save_checkpoint(state, filename="test_chk.json")
    assert chk_path.exists()

    # Load and verify
    loaded, err = wd.load_and_verify_checkpoint("test_chk.json")
    assert err is None
    assert loaded == state

    # Corrupt file
    with open(chk_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["state"]["capital"] = 999999.0  # Tampered
    with open(chk_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    corrupted, err = wd.load_and_verify_checkpoint("test_chk.json")
    assert corrupted is None
    assert "corrupted" in err.lower()
    assert wd.status.safe_mode_active is True
