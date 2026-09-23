"""
Crypto Trading Platform — Data Quality & Lineage Engine.

Institutional gatekeeper auditing data integrity and lineage provenance:
- Impossible OHLC detection (Low > High, Open/Close out of bounds, Zero/Negative prices)
- Duplicate timestamp rejection & out-of-order sequence detection
- Missing-bar gap quantification & completeness score
- Negative and anomalous volume detection
- Cryptographic SHA-256 lineage dataset hashing for immutable research provenance
- Automated sanitization and clean certification verdicts
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from market_data.primitives import Candle

TF_SECONDS_MAP: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


class DataCertificationVerdict(str, Enum):
    CERTIFIED_CLEAN = "CERTIFIED_CLEAN"
    USABLE_WITH_WARNINGS = "USABLE_WITH_WARNINGS"
    REJECTED_CORRUPT = "REJECTED_CORRUPT"


@dataclass
class AnomalyRecord:
    anomaly_type: str
    bar_index: int
    timestamp: int
    details: str


@dataclass
class DataQualityReport:
    symbol: str
    timeframe: str
    total_bars: int
    start_timestamp: int
    end_timestamp: int
    expected_bars: int
    completeness_pct: float
    quality_score: float  # 0.0 to 100.0
    verdict: DataCertificationVerdict
    sha256_dataset_hash: str
    anomalies_count: int
    anomalies_by_type: Dict[str, int]
    gaps: List[Dict[str, Any]]
    sample_anomalies: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_bars": self.total_bars,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "expected_bars": self.expected_bars,
            "completeness_pct": round(self.completeness_pct, 2),
            "quality_score": round(self.quality_score, 2),
            "verdict": self.verdict.value,
            "sha256_dataset_hash": self.sha256_dataset_hash,
            "anomalies_count": self.anomalies_count,
            "anomalies_by_type": self.anomalies_by_type,
            "gaps": self.gaps[:10],
            "sample_anomalies": self.sample_anomalies[:10],
        }


class DataQualityEngine:
    """
    Data Quality and Provenance Gatekeeper for the platform.
    """

    @classmethod
    def compute_dataset_hash(cls, candles: List[Candle]) -> str:
        """
        Computes deterministic SHA-256 hash over candlestick sequences.
        Guarantees exact dataset reproducibility for research lineage.
        """
        hasher = hashlib.sha256()
        for c in candles:
            chunk = f"{c.timestamp}:{c.open:.6f}:{c.high:.6f}:{c.low:.6f}:{c.close:.6f}:{c.volume:.4f},"
            hasher.update(chunk.encode("utf-8"))
        return hasher.hexdigest()

    @classmethod
    def audit_candles(
        cls,
        symbol: str,
        timeframe: str,
        candles: List[Candle],
    ) -> DataQualityReport:
        """
        Performs exhaustive mathematical and structural audit on a sequence of candles.
        """
        tf_clean = timeframe.lower()
        interval_sec = TF_SECONDS_MAP.get(tf_clean, 900)

        if not candles:
            return DataQualityReport(
                symbol=symbol,
                timeframe=timeframe,
                total_bars=0,
                start_timestamp=0,
                end_timestamp=0,
                expected_bars=0,
                completeness_pct=0.0,
                quality_score=0.0,
                verdict=DataCertificationVerdict.REJECTED_CORRUPT,
                sha256_dataset_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                anomalies_count=0,
                anomalies_by_type={},
                gaps=[],
                sample_anomalies=[],
            )

        anomalies: List[AnomalyRecord] = []
        anomalies_by_type: Dict[str, int] = {}
        gaps: List[Dict[str, Any]] = []

        def _record_anomaly(atype: str, idx: int, ts: int, details: str):
            anomalies.append(AnomalyRecord(atype, idx, ts, details))
            anomalies_by_type[atype] = anomalies_by_type.get(atype, 0) + 1

        seen_timestamps = set()
        prev_ts = -1

        for i, c in enumerate(candles):
            # 1. Zero / Negative Price Checks
            if c.open <= 0 or c.high <= 0 or c.low <= 0 or c.close <= 0:
                _record_anomaly("ZERO_OR_NEGATIVE_PRICE", i, c.timestamp, f"O={c.open}, H={c.high}, L={c.low}, C={c.close}")

            # 2. Impossible OHLC Geometry
            if c.low > c.high:
                _record_anomaly("IMPOSSIBLE_OHLC_LOW_GT_HIGH", i, c.timestamp, f"Low {c.low} > High {c.high}")
            if c.open > c.high or c.open < c.low:
                _record_anomaly("IMPOSSIBLE_OHLC_OPEN_OUT_OF_BOUNDS", i, c.timestamp, f"Open {c.open} outside [{c.low}, {c.high}]")
            if c.close > c.high or c.close < c.low:
                _record_anomaly("IMPOSSIBLE_OHLC_CLOSE_OUT_OF_BOUNDS", i, c.timestamp, f"Close {c.close} outside [{c.low}, {c.high}]")

            # 3. Negative Volume
            if c.volume < 0:
                _record_anomaly("NEGATIVE_VOLUME", i, c.timestamp, f"Volume {c.volume} < 0")

            # 4. Duplicate Timestamp
            if c.timestamp in seen_timestamps:
                _record_anomaly("DUPLICATE_TIMESTAMP", i, c.timestamp, f"Duplicate timestamp {c.timestamp}")
            seen_timestamps.add(c.timestamp)

            # 5. Non-monotonic / Out of order
            if prev_ts != -1:
                if c.timestamp < prev_ts:
                    _record_anomaly("NON_MONOTONIC_TIMESTAMP", i, c.timestamp, f"Timestamp {c.timestamp} < Previous {prev_ts}")
                elif (c.timestamp - prev_ts) > interval_sec:
                    # Missing bar gap
                    missing = int((c.timestamp - prev_ts) // interval_sec) - 1
                    gaps.append({
                        "bar_index": i,
                        "from_timestamp": prev_ts,
                        "to_timestamp": c.timestamp,
                        "gap_seconds": c.timestamp - prev_ts,
                        "missing_bars": missing,
                    })

            prev_ts = c.timestamp

        start_ts = candles[0].timestamp
        end_ts = candles[-1].timestamp
        total_span_sec = max(interval_sec, end_ts - start_ts)
        expected_bars = int(total_span_sec // interval_sec) + 1
        actual_bars = len(candles)

        completeness_pct = min(100.0, (actual_bars / expected_bars) * 100.0) if expected_bars > 0 else 100.0

        # Quality scoring (100 base, deductions for anomalies and missing bars)
        deductions = 0.0
        deductions += anomalies_by_type.get("ZERO_OR_NEGATIVE_PRICE", 0) * 10.0
        deductions += anomalies_by_type.get("IMPOSSIBLE_OHLC_LOW_GT_HIGH", 0) * 10.0
        deductions += anomalies_by_type.get("IMPOSSIBLE_OHLC_OPEN_OUT_OF_BOUNDS", 0) * 5.0
        deductions += anomalies_by_type.get("IMPOSSIBLE_OHLC_CLOSE_OUT_OF_BOUNDS", 0) * 5.0
        deductions += anomalies_by_type.get("DUPLICATE_TIMESTAMP", 0) * 2.0
        deductions += anomalies_by_type.get("NON_MONOTONIC_TIMESTAMP", 0) * 5.0
        deductions += (100.0 - completeness_pct) * 0.5

        quality_score = max(0.0, min(100.0, 100.0 - deductions))

        if quality_score >= 95.0 and len(anomalies) == 0 and completeness_pct >= 98.0:
            verdict = DataCertificationVerdict.CERTIFIED_CLEAN
        elif quality_score >= 75.0 and not anomalies_by_type.get("IMPOSSIBLE_OHLC_LOW_GT_HIGH", 0):
            verdict = DataCertificationVerdict.USABLE_WITH_WARNINGS
        else:
            verdict = DataCertificationVerdict.REJECTED_CORRUPT

        dataset_hash = cls.compute_dataset_hash(candles)

        return DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_bars=actual_bars,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            expected_bars=expected_bars,
            completeness_pct=completeness_pct,
            quality_score=quality_score,
            verdict=verdict,
            sha256_dataset_hash=dataset_hash,
            anomalies_count=len(anomalies),
            anomalies_by_type=anomalies_by_type,
            gaps=gaps,
            sample_anomalies=[asdict(a) for a in anomalies[:10]],
        )

    @classmethod
    def sanitize_candles(cls, candles: List[Candle]) -> Tuple[List[Candle], List[str]]:
        """
        Sanitizes candle sequence: removes duplicates, enforces monotonic order,
        and filters out impossible OHLC geometry.
        """
        actions_taken = []
        if not candles:
            return [], actions_taken

        # 1. Filter out impossible prices
        valid = []
        for c in candles:
            if c.low > c.high or c.open < c.low or c.open > c.high or c.close < c.low or c.close > c.high:
                actions_taken.append(f"Filtered impossible bar at ts={c.timestamp}")
                continue
            if c.open <= 0 or c.high <= 0 or c.low <= 0 or c.close <= 0:
                actions_taken.append(f"Filtered non-positive price bar at ts={c.timestamp}")
                continue
            valid.append(c)

        # 2. Sort monotonically by timestamp
        sorted_candles = sorted(valid, key=lambda x: x.timestamp)
        if [c.timestamp for c in valid] != [c.timestamp for c in sorted_candles]:
            actions_taken.append("Sorted out-of-order bars into monotonic order")

        # 3. Deduplicate
        deduped: List[Candle] = []
        seen = set()
        for c in sorted_candles:
            if c.timestamp in seen:
                actions_taken.append(f"Removed duplicate bar at ts={c.timestamp}")
                continue
            seen.add(c.timestamp)
            deduped.append(c)

        return deduped, actions_taken
