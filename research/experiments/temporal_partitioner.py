"""
Product 04 — Research Laboratory: Multi-Period Temporal Partitioning & Walk-Forward Windows
Defines strictly disjoint in-sample, validation benchmark, out-of-sample partitions,
and rolling walk-forward window schedules.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class TemporalPartition:
    partition_id: str
    partition_type: str  # IN_SAMPLE, VALIDATION, OUT_OF_SAMPLE, FORWARD_UNTOUCHED
    start_date: str      # YYYY-MM-DD
    end_date: str        # YYYY-MM-DD
    start_timestamp_utc: int
    end_timestamp_utc: int
    regime_description: str


@dataclass
class WalkForwardWindow:
    window_id: str
    train_start_date: str
    train_end_date: str
    test_start_date: str
    test_end_date: str


class TemporalPartitioner:
    """
    Manages multi-year chronological partitions to guarantee out-of-sample data isolation.
    """

    # Canonical Partitions
    PARTITIONS: Dict[str, TemporalPartition] = {
        "IS_DEVELOPMENT": TemporalPartition(
            partition_id="IS_DEVELOPMENT",
            partition_type="IN_SAMPLE",
            start_date="2021-01-01",
            end_date="2023-01-01",
            start_timestamp_utc=1609459200,
            end_timestamp_utc=1672531200,
            regime_description="2021 Bull Run & 2022 Full Bear Market Cycle"
        ),
        "VALIDATION_BENCHMARK": TemporalPartition(
            partition_id="VALIDATION_BENCHMARK",
            partition_type="VALIDATION",
            start_date="2023-01-01",
            end_date="2024-01-01",
            start_timestamp_utc=1672531200,
            end_timestamp_utc=1704067200,
            regime_description="2023 Accumulation & Recovery Regime"
        ),
        "OOS_1_EXPANSION": TemporalPartition(
            partition_id="OOS_1_EXPANSION",
            partition_type="OUT_OF_SAMPLE",
            start_date="2024-01-01",
            end_date="2025-01-01",
            start_timestamp_utc=1704067200,
            end_timestamp_utc=1735689600,
            regime_description="2024 ETF Expansion & Breakout Rally"
        ),
        "OOS_2_FORWARD": TemporalPartition(
            partition_id="OOS_2_FORWARD",
            partition_type="FORWARD_UNTOUCHED",
            start_date="2025-01-01",
            end_date="2026-08-20",
            start_timestamp_utc=1735689600,
            end_timestamp_utc=1787184000,
            regime_description="2025-2026 Forward Live Shadow Horizon"
        )
    }

    # Rolling Walk-Forward Windows
    WALK_FORWARD_SCHEDULE: List[WalkForwardWindow] = [
        WalkForwardWindow("WF_WINDOW_1", "2021-01-01", "2022-01-01", "2022-01-01", "2023-01-01"),
        WalkForwardWindow("WF_WINDOW_2", "2021-01-01", "2023-01-01", "2023-01-01", "2024-01-01"),
        WalkForwardWindow("WF_WINDOW_3", "2021-01-01", "2024-01-01", "2024-01-01", "2025-01-01"),
        WalkForwardWindow("WF_WINDOW_4", "2021-01-01", "2025-01-01", "2025-01-01", "2026-08-20")
    ]

    @staticmethod
    def partition_trades_by_time(
        trades: List[Dict[str, Any]],
        partition_id: str
    ) -> List[Dict[str, Any]]:
        """
        Filters a collection of trades strictly within the timestamp bounds of a partition.
        """
        p = TemporalPartitioner.PARTITIONS.get(partition_id)
        if not p:
            return []

        matched = []
        for t in trades:
            ts = t.get("setup_timestamp") or t.get("entry_timestamp") or 0
            if p.start_timestamp_utc <= ts < p.end_timestamp_utc:
                matched.append(t)
        return matched

    @staticmethod
    def evaluate_walk_forward_consistency(
        window_expectancies: List[float]
    ) -> Tuple[Optional[float], bool, str]:
        """
        Evaluates whether expectancy is consistently positive across walk-forward rolling test windows.
        """
        if not window_expectancies:
            return None, False, "NO_WINDOWS_TESTED"

        positive_windows = sum(1 for exp in window_expectancies if exp > 0.0)
        total_windows = len(window_expectancies)
        consistency_pct = (positive_windows / total_windows) * 100.0

        if consistency_pct >= 75.0:
            return consistency_pct, True, "CONSISTENT_WALK_FORWARD_EDGE"
        elif consistency_pct >= 50.0:
            return consistency_pct, False, "DEGRADED_WALK_FORWARD_EDGE"
        else:
            return consistency_pct, False, "OVERFIT_WALK_FORWARD_EDGE"
