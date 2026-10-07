"""
QCP Risk Engine — Data Validator.

Validates market data integrity for research/trading readiness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class DataQualityLevel(str, Enum):
    CERTIFIED = "CERTIFIED"
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class DataValidationResult:
    symbol: str
    timeframe: str
    quality_level: DataQualityLevel
    total_rows: int
    valid_rows: int
    issues: List[str] = field(default_factory=list)
    stale_minutes: float = 0.0
    missing_count: int = 0
    duplicate_count: int = 0
    price_outlier_count: int = 0
    timestamp_gap_max_seconds: float = 0.0
    is_tradeable: bool = False
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class DataValidator:
    """Validates a price/volume DataFrame for research or trading readiness."""

    def __init__(
        self,
        max_staleness_minutes: float = 30.0,
        max_missing_fraction: float = 0.01,
        max_duplicate_fraction: float = 0.001,
        max_price_jump: float = 0.15,
        max_timestamp_gap_seconds: float = 3600.0,
    ):
        self.max_staleness_minutes = max_staleness_minutes
        self.max_missing_fraction = max_missing_fraction
        self.max_duplicate_fraction = max_duplicate_fraction
        self.max_price_jump = max_price_jump
        self.max_timestamp_gap_seconds = max_timestamp_gap_seconds

    def validate(self, df, symbol: str = "UNKNOWN", timeframe: str = "1h") -> DataValidationResult:
        issues: List[str] = []
        total = len(df)

        if total == 0:
            return DataValidationResult(symbol=symbol, timeframe=timeframe, quality_level=DataQualityLevel.UNAVAILABLE, total_rows=0, valid_rows=0, is_tradeable=False, issues=["NO_DATA"])

        # Timestamp ordering
        if "timestamp" in df.columns:
            ts = df["timestamp"].values
            if np.any(np.diff(ts) < 0):
                issues.append("TIMESTAMP_NOT_MONOTONIC")
        else:
            issues.append("MISSING_TIMESTAMP_COLUMN")

        # Missing values
        numeric_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        total_missing = sum(int(df[c].isna().sum()) for c in numeric_cols)
        missing_frac = total_missing / (total * max(1, len(numeric_cols)))
        if missing_frac > self.max_missing_fraction:
            issues.append(f"HIGH_MISSING: {missing_frac:.4f}")
        missing_count = int(total_missing)

        # Duplicates
        dup_count = int(df.duplicated().sum())
        if dup_count / max(1, total) > self.max_duplicate_fraction:
            issues.append("HIGH_DUPLICATES")
        duplicate_count = dup_count

        # Price jumps
        price_outliers = 0
        if "close" in df.columns and len(df) > 1:
            close = df["close"].values.astype(float)
            jumps = np.abs((close[1:] - close[:-1]) / np.maximum(close[:-1], 1e-9))
            price_outliers = int(np.sum(jumps > self.max_price_jump))
            if price_outliers > 0:
                issues.append(f"PRICE_JUMPS: {price_outliers}")

        # HLC consistency
        if all(c in df.columns for c in ["high", "low", "close"]):
            h, l, c = df["high"].values, df["low"].values, df["close"].values
            bad = int(np.sum((h < l) | (c > h) | (c < l)))
            if bad > 0:
                issues.append(f"HLC_BAD: {bad}")

        # Timestamp gaps
        max_gap = 0.0
        if "timestamp" in df.columns and len(df) > 1:
            gaps = np.diff(df["timestamp"].values.astype(float))
            max_gap = float(np.max(gaps))
            if max_gap > self.max_timestamp_gap_seconds:
                issues.append(f"GAP: {max_gap:.0f}s")

        # Staleness
        stale_min = 0.0
        if "timestamp" in df.columns:
            last = df["timestamp"].iloc[-1]
            if hasattr(last, "timestamp"):
                stale_min = (datetime.now(timezone.utc) - last).total_seconds() / 60.0
            elif isinstance(last, (int, float)):
                stale_min = (datetime.now(timezone.utc).timestamp() - last) / 60.0
            if stale_min > self.max_staleness_minutes:
                issues.append(f"STALE: {stale_min:.1f}min")

        is_tradeable = (len(issues) == 0 and missing_frac <= self.max_missing_fraction
                        and dup_count / max(1, total) <= self.max_duplicate_fraction
                        and stale_min <= self.max_staleness_minutes)

        if not is_tradeable:
            quality = DataQualityLevel.INVALID if stale_min > self.max_staleness_minutes * 2 or missing_count > total * 0.05 else DataQualityLevel.SUSPECT
        else:
            quality = DataQualityLevel.CERTIFIED if missing_count == 0 and dup_count == 0 else DataQualityLevel.VALID

        return DataValidationResult(symbol=symbol, timeframe=timeframe, quality_level=quality, total_rows=total, valid_rows=total - missing_count, issues=issues, stale_minutes=round(stale_min, 2), missing_count=missing_count, duplicate_count=duplicate_count, price_outlier_count=price_outliers, timestamp_gap_max_seconds=round(max_gap, 2), is_tradeable=is_tradeable)
