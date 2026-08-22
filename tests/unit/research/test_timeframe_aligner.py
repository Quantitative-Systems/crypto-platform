"""
Unit Tests for Product 04: Timeframe Aligner & Causal Visibility
"""

import pytest
from market_intelligence.primitives import Candle
from research.replayer.timeframe_aligner import TimeframeAligner, CANONICAL_TIMEFRAME_SETS


def make_candle(ts: int, close_p: float = 100.0) -> Candle:
    return Candle(
        timestamp=ts,
        open=close_p,
        high=close_p + 1.0,
        low=close_p - 1.0,
        close=close_p,
        volume=100.0
    )


def test_canonical_sets_completeness():
    assert "SET_1" in CANONICAL_TIMEFRAME_SETS
    assert "SET_2" in CANONICAL_TIMEFRAME_SETS
    assert "SET_3" in CANONICAL_TIMEFRAME_SETS
    assert "SET_4" in CANONICAL_TIMEFRAME_SETS

    s4 = TimeframeAligner.get_set("SET_4")
    assert s4.htf == "4H"
    assert s4.mtf == "1H"
    assert s4.ltf == "15M"


def test_point_in_time_filtering_excludes_future_and_open_candles():
    # 1H duration is 3,600,000 ms
    # Candle 1: starts at 0 -> closes at 3,600,000
    # Candle 2: starts at 3,600,000 -> closes at 7,200,000
    # Candle 3: starts at 7,200,000 -> closes at 10,800,000
    candles = [
        make_candle(1_000_000_000_000, 100.0),
        make_candle(1_000_003_600_000, 101.0),
        make_candle(1_000_007_200_000, 102.0)
    ]

    # At decision time T = 5,000,000:
    # Only Candle 1 has closed (0 + 3600000 <= 5000000)
    # Candle 2 is still open (3600000 + 3600000 = 7200000 > 5000000)
    visible = TimeframeAligner.filter_visible_candles(candles, decision_timestamp=1_000_005_000_000, timeframe="1H")
    assert len(visible) == 1
    assert visible[0].timestamp == 1_000_000_000_000

    # At decision time T = 7,200,000:
    # Candle 1 and Candle 2 have closed
    visible = TimeframeAligner.filter_visible_candles(candles, decision_timestamp=1_000_007_200_000, timeframe="1H")
    assert len(visible) == 2
    assert [c.timestamp for c in visible] == [1_000_000_000_000, 1_000_003_600_000]


def test_invalid_set_raises():
    with pytest.raises(ValueError):
        TimeframeAligner.get_set("INVALID_SET")
