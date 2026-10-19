"""Regression tests for Phase R Decision Record deserialization and fail-closed restart recovery."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.persistence.database import DatabaseManager
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.decision.phase_r_decision_engine import (
    DecisionType,
    PhaseRDecisionRecord,
)
from execution.state.state_persistence import (
    PersistenceMode,
    StatePersistenceManager,
)


@pytest.fixture(autouse=True)
def cleanup_databases():
    """Ensure all open database instances are reset after every test."""
    yield
    DatabaseManager.reset_all()


def _create_sample_decision_dict(index: int = 0, decision: str = "NO_TRADE") -> dict:
    """Helper creating a canonical serialized PhaseRDecisionRecord dictionary."""
    return {
        "decision_id": f"DEC_TEST_{index:04d}",
        "lineage_id": f"LIN_TEST_{index:04d}",
        "event_id": f"EVT_TEST_{index:04d}",
        "timestamp_ms": 1700000000000 + index * 60000,
        "asset": "BTCUSDT",
        "timeframe_set": "SET_2",
        "phase": "CONTINUATION",
        "decision": decision,
        "reason_codes": ["NO_STRUCTURAL_SETUP"] if decision == "NO_TRADE" else [],
        "confidence_score": 0.45,
        "confidence_components": {"trend": 0.50, "structure": 0.40},
        "fractal_alignment": "FULLY_ALIGNED",
        "fractal_bias": "BULLISH",
        "direction": 1,
        "entry_price": 60000.0,
        "initial_stop_price": 59000.0,
        "target_price": 65000.0,
        "planned_r": 5.0,
        "risk_pct": 0.01,
        "portfolio_heat_pct": 0.01,
        "governor_passed": True,
        "execution_mode": "SHADOW_PAPER",
        "htf_state_trend": "NEUTRAL",
        "mtf_state_trend": "NEUTRAL",
        "ltf_state_trend": "NEUTRAL",
        "created_at_utc": "2026-10-19T00:00:00Z",
    }


def test_phase_r_decision_record_serialization_roundtrip():
    """Verify PhaseRDecisionRecord roundtrips between to_dict() and from_dict() without NameError."""
    sample = _create_sample_decision_dict(0, "TRADE")
    record = PhaseRDecisionRecord.from_dict(sample)

    assert record.decision_id == "DEC_TEST_0000"
    assert record.decision == DecisionType.TRADE
    assert record.asset == "BTCUSDT"
    assert record.timeframe_set == "SET_2"
    assert record.confidence_score == 0.45
    assert record.target_price == 65000.0

    serialized = record.to_dict()
    assert serialized["decision"] == "TRADE"
    assert serialized["decision_id"] == "DEC_TEST_0000"

    restored = PhaseRDecisionRecord.from_dict(serialized)
    assert restored.decision_id == record.decision_id
    assert restored.decision == record.decision
    assert restored.confidence_components == record.confidence_components


def test_restart_recovery_with_36_valid_historical_decision_records():
    """Verify restart recovery reconciles cleanly and recovers healthy when 36 valid historical records exist."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_file = tmp_path / "test_recovery_36.db"
        state_dir = tmp_path / "state"
        ledger_file = tmp_path / "PHASE_R_DECISION_LEDGER.jsonl"

        # 1. Save valid checkpoint in isolated SQLite DB
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        pm.save_checkpoint(
            equity_usd=100000.0,
            peak_equity_usd=100000.0,
            active_positions=[],
            closed_positions=[],
            orders_history=[],
            fills_history=[],
        )
        pm.close()
        DatabaseManager.reset_all()

        # 2. Persist 36 valid historical records to the ledger file
        with open(ledger_file, "w", encoding="utf-8") as f:
            for i in range(36):
                f.write(json.dumps(_create_sample_decision_dict(i, "NO_TRADE")) + "\n")

        # 3. Boot supervisor targeting the isolated database and ledger
        supervisor = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            state_dir=state_dir,
            db_path=db_file,
            ledger_path=ledger_file,
        )
        try:
            assert supervisor.system_status == "RECOVERED_HEALTHY"
            assert not supervisor.is_persistence_blocked()
            assert len(supervisor.decisions_history) == 36

            recon = supervisor.reconciliation_engine.last_report
            assert recon is not None
            assert recon.is_reconciled is True
            assert recon.status == "RECONCILED"
            assert recon.total_decisions == 36
            assert recon.ledger_records == 36
            assert len(recon.discrepancies) == 0
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_restart_recovery_with_corrupted_ledger_fails_closed():
    """Verify that a genuinely corrupted ledger file aborts restart recovery and halts fail-closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_file = tmp_path / "test_corrupted_ledger.db"
        state_dir = tmp_path / "state"
        ledger_file = tmp_path / "PHASE_R_DECISION_LEDGER.jsonl"

        # 1. Save valid checkpoint
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        pm.save_checkpoint(
            equity_usd=100000.0,
            peak_equity_usd=100000.0,
            active_positions=[],
            closed_positions=[],
            orders_history=[],
            fills_history=[],
        )
        pm.close()
        DatabaseManager.reset_all()

        # 2. Write 5 valid records followed by a corrupted non-JSON line, followed by valid
        with open(ledger_file, "w", encoding="utf-8") as f:
            for i in range(5):
                f.write(json.dumps(_create_sample_decision_dict(i, "NO_TRADE")) + "\n")
            f.write("CORRUPTED_NON_JSON_RECORD_DATA_LINE\n")
            for i in range(6, 10):
                f.write(json.dumps(_create_sample_decision_dict(i, "NO_TRADE")) + "\n")

        # 3. Boot supervisor targeting the corrupted ledger
        supervisor = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            state_dir=state_dir,
            db_path=db_file,
            ledger_path=ledger_file,
        )
        try:
            assert supervisor.system_status == "RECOVERY_FAILED_HALTED"
            assert supervisor.is_persistence_blocked() is True

            # Attempting to start supervisor must abort and raise RuntimeError
            with pytest.raises(RuntimeError, match="RECOVERY_FAILED_HALTED"):
                import asyncio
                asyncio.run(supervisor.start())
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()


def test_historical_seeding_preserves_failed_recovery_state():
    """Verify that seed_historical_state() preserves RECOVERY_FAILED_HALTED and does not overwrite it with SEEDED_READY."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_file = tmp_path / "test_seed_preserves_halt.db"
        state_dir = tmp_path / "state"
        ledger_file = tmp_path / "PHASE_R_DECISION_LEDGER.jsonl"

        # 1. Save valid checkpoint
        pm = StatePersistenceManager(state_dir=state_dir, db_path=db_file, mode=PersistenceMode.REQUIRED_DURABLE)
        pm.save_checkpoint(
            equity_usd=100000.0,
            peak_equity_usd=100000.0,
            active_positions=[],
            closed_positions=[],
            orders_history=[],
            fills_history=[],
        )
        pm.close()
        DatabaseManager.reset_all()

        # 2. Write invalid record missing mandatory fields
        with open(ledger_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"invalid_schema": True, "timestamp_ms": 1700000000000}) + "\n")

        # 3. Boot supervisor: it must halt fail-closed
        supervisor = AutonomousTradingSupervisor(
            symbols=["BTCUSDT"],
            state_dir=state_dir,
            db_path=db_file,
            ledger_path=ledger_file,
        )
        try:
            assert supervisor.system_status == "RECOVERY_FAILED_HALTED"
            assert supervisor.is_persistence_blocked() is True

            # 4. Attempt to run seed_historical_state() as done in main.py
            seeded_counts = supervisor.seed_historical_state()

            # It MUST preserve the failed recovery state and NOT clobber with SEEDED_READY
            assert supervisor.system_status == "RECOVERY_FAILED_HALTED"
            assert supervisor.is_persistence_blocked() is True
            assert seeded_counts == {"BTCUSDT": 0}

            # Attempting to start must still be blocked with RECOVERY_FAILED_HALTED
            with pytest.raises(RuntimeError, match="RECOVERY_FAILED_HALTED"):
                import asyncio
                asyncio.run(supervisor.start())
        finally:
            supervisor.state_persistence.close()
            DatabaseManager.reset_all()
