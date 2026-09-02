"""
Unit tests for In-Sample (IS) and Out-Of-Sample (OOS) data partitioning and retention metrics.
"""

import pytest
from research.experiments.run_oos_validation import analyze_trade_set


def test_analyze_trade_set_metrics_accuracy():
    """Verifies that analyze_trade_set computes exact mathematical aggregates."""
    trades = [
        {"net_pnl": 500.0, "net_r": 5.0, "directional_permission": "PERMIT_LONG", "exit_reason": "HTF_TP"},
        {"net_pnl": -100.0, "net_r": -1.0, "directional_permission": "PERMIT_LONG", "exit_reason": "INITIAL_LTF_SL"},
        {"net_pnl": 200.0, "net_r": 2.0, "directional_permission": "PERMIT_SHORT", "exit_reason": "MTF_STRUCTURAL_TRAIL"},
    ]

    stats = analyze_trade_set(trades)
    assert stats["total_trades"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["win_rate_pct"] == pytest.approx(66.6666, rel=1e-3)
    assert stats["gross_profit"] == 700.0
    assert stats["gross_loss"] == 100.0
    assert stats["profit_factor"] == 7.0
    assert stats["net_pnl"] == 600.0
    assert stats["total_realized_r"] == 6.0
    assert stats["expectancy_r"] == 2.0
    assert stats["long_trades"] == 2
    assert stats["short_trades"] == 1
    assert stats["exit_attribution"]["HTF_TP"] == 1
    assert stats["exit_attribution"]["INITIAL_LTF_SL"] == 1


def test_is_oos_trade_partitioning_disjoint():
    """Proves that chronological split partitions trades into strictly disjoint subsets."""
    split_timestamp = 1700000000

    all_trades = [
        {"trade_id": "t1", "setup_timestamp": 1699990000, "net_pnl": 100.0, "net_r": 1.0},
        {"trade_id": "t2", "setup_timestamp": 1699995000, "net_pnl": -50.0, "net_r": -1.0},
        {"trade_id": "t3", "setup_timestamp": 1700000000, "net_pnl": 200.0, "net_r": 2.0},
        {"trade_id": "t4", "setup_timestamp": 1700010000, "net_pnl": 300.0, "net_r": 3.0},
    ]

    is_trades = [t for t in all_trades if t["setup_timestamp"] < split_timestamp]
    oos_trades = [t for t in all_trades if t["setup_timestamp"] >= split_timestamp]

    # Verify disjoint sets
    is_ids = {t["trade_id"] for t in is_trades}
    oos_ids = {t["trade_id"] for t in oos_trades}

    assert is_ids == {"t1", "t2"}
    assert oos_ids == {"t3", "t4"}
    assert is_ids.isdisjoint(oos_ids)
    assert len(is_trades) + len(oos_trades) == len(all_trades)
