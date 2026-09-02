"""
Unit tests for DataManager 5-stage certification pipeline and candle invariant validation.
"""

import pytest
from market_intelligence.primitives import Candle
from market_data.data_manager import DataManager, CertificationState


def test_validate_candle_integrity_valid_series():
    candles = [
        Candle(timestamp=1000, open=100.0, high=105.0, low=95.0, close=102.0, volume=10.0),
        Candle(timestamp=1060, open=102.0, high=108.0, low=101.0, close=106.0, volume=15.0),
        Candle(timestamp=1120, open=106.0, high=107.0, low=100.0, close=101.0, volume=12.0),
    ]
    report = DataManager.validate_candle_integrity(candles, "1m")
    assert report["valid"] is True
    assert report["total_candles"] == 3
    assert report["ohlc_violations"] == 0
    assert report["timestamp_violations"] == 0
    assert report["volume_violations"] == 0


def test_validate_candle_integrity_detects_ohlc_violation():
    # High is less than Open (invalid OHLC geometry)
    candles = [
        Candle(timestamp=1000, open=100.0, high=95.0, low=90.0, close=92.0, volume=10.0),
    ]
    report = DataManager.validate_candle_integrity(candles, "1m")
    assert report["valid"] is False
    assert report["ohlc_violations"] == 1


def test_validate_candle_integrity_detects_timestamp_disorder():
    # Timestamps are non-increasing
    candles = [
        Candle(timestamp=1060, open=100.0, high=105.0, low=95.0, close=102.0, volume=10.0),
        Candle(timestamp=1000, open=102.0, high=108.0, low=101.0, close=106.0, volume=15.0),
    ]
    report = DataManager.validate_candle_integrity(candles, "1m")
    assert report["valid"] is False
    assert report["timestamp_violations"] == 1


def test_certify_dataset_pipeline_full_lifecycle():
    # Build 60 valid 1-hour candles
    candles = []
    base_ts = 1700000000
    for i in range(60):
        candles.append(
            Candle(
                timestamp=base_ts + (i * 3600),
                open=50000.0 + i,
                high=50050.0 + i,
                low=49950.0 + i,
                close=50020.0 + i,
                volume=100.0
            )
        )
    state, report = DataManager.certify_dataset_pipeline(candles, "1h", "BTC/USDT")
    assert state == CertificationState.RESEARCH_ELIGIBLE
    assert report["stage_reached"] == CertificationState.RESEARCH_ELIGIBLE.value
    assert "PASSED" in report["checks"]["research_eligible"]
