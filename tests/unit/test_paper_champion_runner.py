"""Tests for Autonomous Shadow/Paper Champion Engine and Demotion Governor."""
from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np

from execution.shadow.paper_champion_runner import PaperChampionEngine


def test_paper_champion_engine_initialization():
    """Verify engine initializes with 0 real capital and loads champions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_ledger.jsonl"
        engine = PaperChampionEngine(
            ledger_path=ledger_path,
            account_equity_usd=100_000.0,
        )
        status = engine.summary_status()
        assert status["total_champions"] >= 0
        assert status["active_open_trades"] == 0
        assert status["completed_paper_trades"] == 0


def test_opportunity_evaluation_and_geometry_gate():
    """Verify valid trades are accepted and invalid geometry is rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_ledger.jsonl"
        engine = PaperChampionEngine(
            ledger_path=ledger_path,
            account_equity_usd=100_000.0,
        )
        # Register test champion
        engine.champions["CHAMP_BTC_TEST"] = engine.champions.get("CHAMP_BTC_TEST") or \
            engine.champions.get(list(engine.champions.keys())[0]) if engine.champions else None
        
        # Manually inject test champion if registry empty
        from execution.shadow.paper_champion_runner import ChampionHealthState
        engine.champions["TEST_CHAMPION"] = ChampionHealthState(
            champion_id="TEST_CHAMPION",
            slot_key="BTCUSDT_SET_2_CONTINUATION",
            status="ACTIVE_PAPER",
        )

        # 1. Valid Long Opportunity (Entry=100, Stop=98, Target=110 -> 5R)
        trade = engine.evaluate_opportunity(
            champion_id="TEST_CHAMPION",
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=100.0,
            stop_price=98.0,
            target_price=110.0,
            timestamp_ms=1000,
        )
        assert trade is not None
        assert trade.status == "OPEN"
        assert trade.target_r == 5.0
        assert trade.predicted_entry == 100.0

        # 2. Inverted Geometry: Target < Entry on Long -> Must Reject
        inv_trade = engine.evaluate_opportunity(
            champion_id="TEST_CHAMPION",
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=100.0,
            stop_price=98.0,
            target_price=95.0,  # INVERTED!
            timestamp_ms=2000,
        )
        assert inv_trade is None, "Inverted target must be rejected!"

        # 3. Sub-4R Target: Target R = 3.0 -> Must Reject
        sub_4r_trade = engine.evaluate_opportunity(
            champion_id="TEST_CHAMPION",
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=100.0,
            stop_price=98.0,
            target_price=106.0,  # Only 3R!
            timestamp_ms=3000,
        )
        assert sub_4r_trade is None, "Sub-4R target must be rejected!"


def test_adverse_first_exit_and_lifecycle():
    """Verify open positions exit adverse-first and record to completed audit list."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_ledger.jsonl"
        engine = PaperChampionEngine(
            ledger_path=ledger_path,
            account_equity_usd=100_000.0,
        )
        from execution.shadow.paper_champion_runner import ChampionHealthState
        engine.champions["TEST_CHAMPION"] = ChampionHealthState(
            champion_id="TEST_CHAMPION",
            slot_key="BTCUSDT_SET_2_CONTINUATION",
            status="ACTIVE_PAPER",
        )

        trade = engine.evaluate_opportunity(
            champion_id="TEST_CHAMPION",
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=100.0,
            stop_price=98.0,
            target_price=110.0,
            timestamp_ms=1000,
        )
        assert trade is not None

        # Next bar: Price hits Target (high=111.0, low=99.0)
        closed = engine.update_open_trades(
            current_low=99.0,
            current_high=111.0,
            current_close=110.5,
            timestamp_ms=2000,
        )
        assert len(closed) == 1
        assert closed[0].exit_reason == "HTF_TP"
        assert closed[0].realized_r > 4.5
        assert len(engine.completed_paper_trades) == 1
        assert len(engine.active_paper_trades) == 0


def test_autonomous_drift_demotion_trigger():
    """Verify champion automatically demotes when rolling performance degrades."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_ledger.jsonl"
        engine = PaperChampionEngine(
            ledger_path=ledger_path,
            account_equity_usd=100_000.0,
        )
        from execution.shadow.paper_champion_runner import ChampionHealthState
        engine.champions["TEST_CHAMPION"] = ChampionHealthState(
            champion_id="TEST_CHAMPION",
            slot_key="BTCUSDT_SET_2_CONTINUATION",
            status="ACTIVE_PAPER",
        )

        # Feed 15 consecutive losing trades (-1.0R each)
        for i in range(16):
            engine._update_champion_drift("TEST_CHAMPION", -1.0)

        champ = engine.champions["TEST_CHAMPION"]
        assert champ.status == "DEMOTED_DRIFT"
        assert champ.demotion_reason is not None

        # Subsequent signals from this champion must now be REJECTED
        new_trade = engine.evaluate_opportunity(
            champion_id="TEST_CHAMPION",
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=100.0,
            stop_price=98.0,
            target_price=110.0,
            timestamp_ms=5000,
        )
        assert new_trade is None, "Demoted champion must be barred from new trades!"
