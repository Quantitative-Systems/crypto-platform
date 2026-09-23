"""
Unit tests for Data Quality & Lineage Engine.
Tests impossible OHLC detection, duplicate detection, missing bar gap tracking,
cryptographic SHA-256 lineage hashing, and automated candle sanitization.
"""

import pytest
from market_data.primitives import Candle
from market_data.data_quality_engine import (
    DataQualityEngine,
    DataCertificationVerdict,
)


def make_clean_candles(count: int = 100, start_ts: int = 1704067200, interval_sec: int = 900):
    candles = []
    p = 100.0
    for i in range(count):
        ts = start_ts + i * interval_sec
        candles.append(
            Candle(
                timestamp=ts,
                open=p,
                high=p + 2.0,
                low=p - 2.0,
                close=p + 0.5,
                volume=500.0,
            )
        )
        p += 0.2
    return candles


def test_audit_clean_data():
    candles = make_clean_candles(count=100)
    report = DataQualityEngine.audit_candles("SOL/USDT", "15m", candles)

    assert report.total_bars == 100
    assert report.completeness_pct == 100.0
    assert report.quality_score == 100.0
    assert report.verdict == DataCertificationVerdict.CERTIFIED_CLEAN
    assert report.anomalies_count == 0
    assert len(report.sha256_dataset_hash) == 64


def test_audit_impossible_ohlc():
    candles = make_clean_candles(count=10)

    # Corrupt bar 3: Low > High
    candles[3] = Candle(
        timestamp=candles[3].timestamp,
        open=100.0,
        high=90.0,
        low=105.0,  # Low > High
        close=95.0,
        volume=100.0,
    )

    # Corrupt bar 5: Close > High
    candles[5] = Candle(
        timestamp=candles[5].timestamp,
        open=100.0,
        high=102.0,
        low=98.0,
        close=108.0,  # Close > High
        volume=100.0,
    )

    report = DataQualityEngine.audit_candles("SOL/USDT", "15m", candles)
    assert report.anomalies_count >= 2
    assert "IMPOSSIBLE_OHLC_LOW_GT_HIGH" in report.anomalies_by_type
    assert "IMPOSSIBLE_OHLC_CLOSE_OUT_OF_BOUNDS" in report.anomalies_by_type
    assert report.verdict == DataCertificationVerdict.REJECTED_CORRUPT


def test_audit_duplicates_and_gaps():
    candles = make_clean_candles(count=20, interval_sec=900)

    # Insert duplicate timestamp at index 5
    dup_bar = Candle(
        timestamp=candles[4].timestamp,  # duplicate
        open=100.0, high=101.0, low=99.0, close=100.5, volume=50.0
    )
    candles.insert(5, dup_bar)

    # Create a 3600s gap at index 10 (jump forward)
    gap_bar = Candle(
        timestamp=candles[10].timestamp + 3600,
        open=102.0, high=103.0, low=101.0, close=102.5, volume=50.0
    )
    candles[11] = gap_bar

    report = DataQualityEngine.audit_candles("ETH/USDT", "15m", candles)
    assert "DUPLICATE_TIMESTAMP" in report.anomalies_by_type
    assert len(report.gaps) >= 1
    assert report.gaps[0]["missing_bars"] >= 1


def test_sanitize_candles():
    corrupt_list = [
        Candle(1000, 10.0, 12.0, 8.0, 11.0, 100.0),  # Valid
        Candle(2000, 10.0, 8.0, 12.0, 9.0, 100.0),   # Impossible: low > high
        Candle(1000, 10.0, 12.0, 8.0, 11.0, 100.0),  # Duplicate
        Candle(3000, 11.0, 13.0, 10.0, 12.0, 100.0), # Valid
        Candle(2500, 10.5, 12.5, 9.5, 11.5, 100.0),  # Out of order timestamp
    ]

    sanitized, actions = DataQualityEngine.sanitize_candles(corrupt_list)
    assert len(sanitized) == 3  # 1000, 2500, 3000
    assert [c.timestamp for c in sanitized] == [1000, 2500, 3000]
    assert len(actions) >= 3


def test_lineage_hash_deterministic():
    candles_a = make_clean_candles(count=25)
    candles_b = make_clean_candles(count=25)

    hash_a = DataQualityEngine.compute_dataset_hash(candles_a)
    hash_b = DataQualityEngine.compute_dataset_hash(candles_b)
    assert hash_a == hash_b

    # Tiniest change to price produces completely different SHA-256 hash
    candles_modified = make_clean_candles(count=25)
    c = candles_modified[10]
    candles_modified[10] = Candle(
        timestamp=c.timestamp,
        open=c.open,
        high=c.high,
        low=c.low,
        close=c.close + 0.0001,
        volume=c.volume,
    )
    hash_mod = DataQualityEngine.compute_dataset_hash(candles_modified)
    assert hash_a != hash_mod
