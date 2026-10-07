"""Unit tests for Phase R Decision Engine, Target Geometry, and Reconciliation."""
import numpy as np
import pytest

from execution.decision.phase_r_decision_engine import (
    DecisionType,
    PhaseRDecisionEngine,
    PhaseRNoTradeReason,
)
from execution.reconciliation_engine import AutonomousReconciliationEngine
from validation.realtime_drift_monitor import DriftState, RealtimeDriftMonitor


def test_decision_engine_set_1_and_set_5_zero_capital_rejections():
    engine = PhaseRDecisionEngine(symbol="BTCUSDT")

    # Generate synthetic dummy data for 7 timeframes
    n_bars = 100
    dummy_data = {
        tf: {
            "ts": np.arange(1000, 1000 + n_bars * 1000, 1000, dtype=np.int64),
            "close_ts": np.arange(2000, 2000 + n_bars * 1000, 1000, dtype=np.int64),
            "o": np.full(n_bars, 60000.0),
            "h": np.full(n_bars, 61000.0),
            "l": np.full(n_bars, 59000.0),
            "c": np.full(n_bars, 60500.0),
            "v": np.full(n_bars, 100.0),
        }
        for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]
    }

    # Evaluate SET_1
    d_set1 = engine.evaluate_opportunity("SET_1", "CONTINUATION", dummy_data)
    assert d_set1.decision == DecisionType.NO_TRADE
    assert PhaseRNoTradeReason.SET_1_MACRO_ANCHOR.value in d_set1.reason_codes

    # Evaluate SET_5
    d_set5 = engine.evaluate_opportunity("SET_5", "PULLBACK", dummy_data)
    assert d_set5.decision == DecisionType.NO_TRADE
    assert PhaseRNoTradeReason.SET_5_MICRO_CONFIRMATION.value in d_set5.reason_codes


def test_reconciliation_engine_passes_consistent_state():
    recon = AutonomousReconciliationEngine()
    decisions = [
        {"decision": "TRADE"},
        {"decision": "NO_TRADE"},
        {"decision": "NO_TRADE"},
    ]
    orders = [{"id": "O1"}]
    fills = [{"id": "F1"}]
    active_pos = [{"id": "P1"}]
    closed_pos = []

    report = recon.reconcile(
        candidate_count=3,
        decisions=decisions,
        orders=orders,
        fills=fills,
        active_positions=active_pos,
        closed_positions=closed_pos,
        ledger_count=3,
    )
    assert report.is_reconciled
    assert report.status == "RECONCILED"
    assert len(report.discrepancies) == 0


def test_reconciliation_engine_catches_discrepancy():
    recon = AutonomousReconciliationEngine()
    decisions = [{"decision": "TRADE"}]
    orders = [{"id": "O1"}]
    fills = [{"id": "F1"}]
    # Fills=1 but active=0 and closed=0 -> discrepancy!
    active_pos = []
    closed_pos = []

    report = recon.reconcile(
        candidate_count=1,
        decisions=decisions,
        orders=orders,
        fills=fills,
        active_positions=active_pos,
        closed_positions=closed_pos,
        ledger_count=1,
    )
    assert not report.is_reconciled
    assert report.status == "DISCREPANCY_DETECTED"
    assert any("Position lifecycle mismatch" in d for d in report.discrepancies)


def test_realtime_drift_monitor_detects_degradation():
    monitor = RealtimeDriftMonitor(min_sample_evaluation=5)
    # Record winning trades initially
    for _ in range(5):
        monitor.record_completed_trade(realized_r=2.0, confidence_score=0.70)
    rep1 = monitor.evaluate_drift()
    assert rep1.drift_state == DriftState.STABLE

    # Now record severe string of losses causing negative expectancy
    for _ in range(15):
        monitor.record_completed_trade(realized_r=-1.0, confidence_score=0.50)
    rep2 = monitor.evaluate_drift()
    assert rep2.drift_state == DriftState.CRITICAL_DRIFT
    assert rep2.action_recommended == "PAUSE_TRADING_FLAG_CRITICAL_INVESTIGATION"
