"""Unit tests for Phase K: Walk-Forward Integrated System Validation.

Validates:
1. Canonical walk-forward fold chronological invariants (train -> test sequencing).
2. System integrity and causality auditor (lookahead & feature leakage detection).
3. Fold metrics computation contracts.
"""
from __future__ import annotations

from execution.backtest.engine import TradeRecord
from market_model.contracts import MarketState, StructureSnapshot, TrendDirection
from validation.walk_forward.contracts import (
    FoldPerformanceMetrics,
    SystemIntegrityCheckRecord,
    WalkForwardFoldSpec,
    WalkForwardPartitionType,
)
from validation.walk_forward.walk_forward_engine import (
    CANONICAL_WALK_FORWARD_FOLDS,
    WalkForwardEngine,
)


def test_canonical_folds_chronology_and_invariants():
    """Verify that all canonical walk-forward folds maintain strict chronological progression."""
    engine = WalkForwardEngine()
    assert len(engine.folds) == 4

    for fold in engine.folds:
        # Train period must precede test period
        assert fold.train_start_ts < fold.train_end_ts
        assert fold.train_end_ts == fold.test_start_ts
        assert fold.test_start_ts < fold.test_end_ts

    # Check Fold 4 is the pure Out-of-Sample evaluation window (2024-2026)
    f4 = engine.folds[3]
    assert f4.fold_name == "FOLD_4_UNSEEN_OOS_2024_2026"
    assert f4.test_start_ts == 1704067200000  # 2024-01-01
    assert f4.test_end_ts == 1788220800000    # 2026-09-01


def test_system_integrity_auditor_zero_violations():
    """Verify integrity auditor passes cleanly on valid causal trade and signal logs."""
    engine = WalkForwardEngine()

    # Valid candidate signal at bar t
    cand_sig = {
        "symbol": "BTCUSDT",
        "timestamp_ms": 1_700_000_000_000,
        "bar_index": 100,
        "direction": 1,
        "h_state": MarketState(symbol="BTCUSDT", timestamp_ms=1_700_000_000_000, timeframe="1w", close_price=50000.0),
        "m_state": MarketState(symbol="BTCUSDT", timestamp_ms=1_700_000_000_000, timeframe="1d", close_price=50000.0),
        "ltf_state": MarketState(symbol="BTCUSDT", timestamp_ms=1_700_000_000_000, timeframe="4h", close_price=50000.0),
    }

    # Trade entered strictly on next bar open (t + 14,400,000 ms)
    trade = TradeRecord(
        symbol="BTCUSDT",
        stream_id="STREAM_TEST",
        direction=1,
        entry_ts=1_700_000_000_000 + 14_400_000,
        exit_ts=1_700_000_000_000 + 72_000_000,
        entry_px=50000.0,
        exit_px=54000.0,
        initial_sl=49000.0,
        target_px=54000.0,
        initial_risk_dist=1000.0,
        target_r=4.0,
        realized_r=4.0,
        exit_reason="HTF_TP",
        bars_held=4,
        fee_bps=15.0,
        slippage_bps=4.0,
    )

    checks = engine.audit_system_integrity([cand_sig], [trade])
    assert len(checks) >= 4
    for c in checks:
        assert c.passed
        assert c.violations_count == 0


def test_system_integrity_auditor_catches_feature_leak():
    """Verify integrity auditor detects future state timestamp leakage."""
    engine = WalkForwardEngine()

    # Candidate with future HTF timestamp leakage (timestamp > signal bar)
    leaked_sig = {
        "symbol": "BTCUSDT",
        "timestamp_ms": 1_700_000_000_000,
        "bar_index": 100,
        "direction": 1,
        "h_state": MarketState(symbol="BTCUSDT", timestamp_ms=1_700_005_000_000, timeframe="1w", close_price=50000.0),  # Leak!
    }

    trade = TradeRecord(
        symbol="BTCUSDT",
        stream_id="STREAM_TEST",
        direction=1,
        entry_ts=1_700_014_400_000,
        exit_ts=1_700_072_000_000,
        entry_px=50000.0,
        exit_px=54000.0,
        initial_sl=49000.0,
        target_px=54000.0,
        initial_risk_dist=1000.0,
        target_r=4.0,
        realized_r=4.0,
        exit_reason="HTF_TP",
        bars_held=4,
        fee_bps=15.0,
        slippage_bps=4.0,
    )

    checks = engine.audit_system_integrity([leaked_sig], [trade])
    feature_check = next(c for c in checks if c.check_name == "CAUSAL_FEATURE_STATE_INVARIANT")
    assert not feature_check.passed
    assert feature_check.violations_count == 1


def test_fold_performance_metrics_calculation():
    """Verify Section 20 metrics calculation across trades in a fold."""
    engine = WalkForwardEngine()
    fold = engine.folds[0]

    t1 = TradeRecord(
        symbol="BTCUSDT", stream_id="S1", direction=1,
        entry_ts=1610000000000, exit_ts=1610100000000,
        entry_px=40000.0, exit_px=44000.0, initial_sl=39000.0, target_px=44000.0,
        initial_risk_dist=1000.0, target_r=4.0, realized_r=3.95, exit_reason="HTF_TP",
        bars_held=5, fee_bps=15.0, slippage_bps=4.0,
    )
    t2 = TradeRecord(
        symbol="BTCUSDT", stream_id="S2", direction=1,
        entry_ts=1610200000000, exit_ts=1610300000000,
        entry_px=42000.0, exit_px=41000.0, initial_sl=41000.0, target_px=46000.0,
        initial_risk_dist=1000.0, target_r=4.0, realized_r=-1.02, exit_reason="LTF_SL",
        bars_held=2, fee_bps=15.0, slippage_bps=4.0,
    )

    m = engine.calc_fold_metrics(
        fold_spec=fold,
        system_id="SYS_INTEGRATED",
        system_name="Complete Integrated System",
        trades=[t1, t2],
        partition_type=WalkForwardPartitionType.WALK_FORWARD_TEST,
    )
    assert m.trade_count == 2
    assert m.net_r == 2.93
    assert m.win_rate == 50.0
    assert m.profit_factor > 3.0
    assert m.max_drawdown_pct > 0.0
