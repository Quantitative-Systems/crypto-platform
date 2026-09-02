"""
Unit tests for TemporalPartitioner.
"""

import pytest
from research.experiments.temporal_partitioner import (
    TemporalPartitioner,
    TemporalPartition
)


def test_temporal_partition_filtering():
    trades = [
        {"trade_id": "t1", "setup_timestamp": 1650000000, "net_r": 1.0}, # 2022 -> IS_DEVELOPMENT
        {"trade_id": "t2", "setup_timestamp": 1680000000, "net_r": 2.0}, # 2023 -> VALIDATION_BENCHMARK
        {"trade_id": "t3", "setup_timestamp": 1710000000, "net_r": 3.0}, # 2024 -> OOS_1_EXPANSION
    ]

    is_trades = TemporalPartitioner.partition_trades_by_time(trades, "IS_DEVELOPMENT")
    bm_trades = TemporalPartitioner.partition_trades_by_time(trades, "VALIDATION_BENCHMARK")
    oos_trades = TemporalPartitioner.partition_trades_by_time(trades, "OOS_1_EXPANSION")

    assert len(is_trades) == 1 and is_trades[0]["trade_id"] == "t1"
    assert len(bm_trades) == 1 and bm_trades[0]["trade_id"] == "t2"
    assert len(oos_trades) == 1 and oos_trades[0]["trade_id"] == "t3"


def test_walk_forward_consistency_evaluation():
    # 4 positive rolling windows (100% consistency)
    windows = [0.35, 0.42, 0.28, 0.50]
    pct, is_consistent, verdict = TemporalPartitioner.evaluate_walk_forward_consistency(windows)
    assert pct == 100.0
    assert is_consistent is True
    assert verdict == "CONSISTENT_WALK_FORWARD_EDGE"

    # Only 1 positive rolling window out of 4 (25% consistency)
    windows_poor = [-0.10, -0.25, 0.15, -0.30]
    pct_p, is_consistent_p, verdict_p = TemporalPartitioner.evaluate_walk_forward_consistency(windows_poor)
    assert pct_p == 25.0
    assert is_consistent_p is False
    assert verdict_p == "OVERFIT_WALK_FORWARD_EDGE"
