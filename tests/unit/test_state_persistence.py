"""Unit tests for STRATA State Checkpointing & Restart Recovery."""
import tempfile
from pathlib import Path
import pytest
from execution.state.state_persistence import StatePersistenceManager


def test_state_persistence_save_and_recover():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = StatePersistenceManager(state_dir=Path(tmpdir))

        # Save checkpoint
        saved = mgr.save_checkpoint(
            equity_usd=105_000.0,
            peak_equity_usd=108_000.0,
            active_positions=[{"symbol": "BTCUSDT", "size": 0.5}],
            closed_trades_count=12,
            metrics={"net_r": 15.4},
            candle_sync_timestamps={"BTCUSDT": 1700000000000},
            circuit_breakers_state={"MaxDrawdownBreaker": "ARMED"},
        )
        assert saved

        # Load checkpoint
        loaded = mgr.load_checkpoint()
        assert loaded is not None
        assert loaded["equity_usd"] == 105_000.0
        assert loaded["peak_equity_usd"] == 108_000.0
        assert loaded["closed_trades_count"] == 12
        assert len(loaded["active_positions"]) == 1
