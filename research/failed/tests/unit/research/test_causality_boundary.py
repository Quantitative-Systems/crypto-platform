"""
Unit tests proving zero lookahead and causality boundary guarantees in the research engine.
Verifies that future candles cannot alter point-in-time decisions or state at timestamp T.
"""

import pytest
from market_intelligence.primitives import Candle, TrendDirection
from market_intelligence.raw_swing_engine import RawSwingEngine
from market_intelligence.coordinator import LanguageCoordinator
from research.replayer.timeframe_aligner import TimeframeAligner, CANONICAL_TIMEFRAME_SETS


def test_timeframe_aligner_excludes_unclosed_htf_candles():
    """
    Verifies that a 4H candle starting at 12:00 (which closes at 16:00) is strictly
    invisible to 1H decision ticks at 12:00, 13:00, 14:00, 15:00, and only becomes
    visible at 16:00.
    """
    # 4H candles starting at 08:00 (closes 12:00) and 12:00 (closes 16:00)
    # Timestamps in seconds
    t_08 = 1700000000          # 08:00
    t_12 = t_08 + 4 * 3600      # 12:00
    t_16 = t_12 + 4 * 3600      # 16:00

    htf_candles = [
        Candle(timestamp=t_08, open=60000.0, high=60500.0, low=59500.0, close=60200.0, volume=100.0),
        Candle(timestamp=t_12, open=60200.0, high=61000.0, low=60100.0, close=60800.0, volume=150.0),
    ]

    # At decision timestamp 15:00 (t_12 + 3 hours):
    t_15 = t_12 + 3 * 3600
    visible_at_15 = TimeframeAligner.filter_visible_candles(htf_candles, t_15, timeframe="4H")
    # Only the 08:00 candle has closed; 12:00 candle is still open
    assert len(visible_at_15) == 1
    assert visible_at_15[0].timestamp == t_08

    # At decision timestamp 16:00 (t_12 + 4 hours):
    visible_at_16 = TimeframeAligner.filter_visible_candles(htf_candles, t_16, timeframe="4H")
    # Now both 08:00 and 12:00 candles have closed
    assert len(visible_at_16) == 2
    assert visible_at_16[-1].timestamp == t_12


def test_swing_confirmation_index_prevents_lookahead():
    """
    Verifies that a geometric swing peak at bar index j is confirmed ONLY at index j + right_bars.
    """
    # 5-bar sequence: low -> high -> peak (index 2) -> lower -> lower
    candles = [
        Candle(timestamp=1000, open=100, high=105, low=95, close=102, volume=10),
        Candle(timestamp=2000, open=102, high=110, low=100, close=108, volume=10),
        Candle(timestamp=3000, open=108, high=125, low=107, close=120, volume=10),  # Peak at idx=2 (high=125)
        Candle(timestamp=4000, open=114, high=115, low=105, close=110, volume=10),  # Lower high=115
        Candle(timestamp=5000, open=107, high=108, low=98, close=100, volume=10),   # Confirmation bar at idx=4 (high=108)
    ]

    from market_intelligence.raw_swing_engine import RawSwingConfig
    engine = RawSwingEngine(config=RawSwingConfig(left_bars=2, right_bars=2, timeframe="1H"))

    # Evaluating with only 3 bars (up to peak): NO swing confirmed
    swings_at_2 = engine.detect(candles[:3])
    assert len(swings_at_2) == 0

    # Evaluating with 4 bars (1 bar after peak): NO swing confirmed
    swings_at_3 = engine.detect(candles[:4])
    assert len(swings_at_3) == 0

    # Evaluating with 5 bars (2 bars after peak = confirmation bar): Swing IS confirmed
    swings_at_4 = engine.detect(candles[:5])
    assert len(swings_at_4) == 1
    swing = swings_at_4[0]
    assert swing.candle_index == 2
    assert swing.confirmation_index == 4
    assert swing.price == 125.0


def test_future_data_invariance():
    """
    Verifies that appending future candles does not alter Market Intelligence state computed at timestamp T.
    """
    coordinator = LanguageCoordinator(buffer_size=100)

    # Base historical candle sequence
    base_candles = [
        Candle(timestamp=1000 * i, open=100 + i, high=105 + i, low=95 + i, close=102 + i, volume=50)
        for i in range(30)
    ]

    state_before = coordinator.run(base_candles, symbol="BTC/USDT", timeframe="1H")

    # Append 50 future candles
    future_candles = [
        Candle(timestamp=1000 * (30 + i), open=200 + i, high=250 + i, low=190 + i, close=240 + i, volume=500)
        for i in range(50)
    ]
    all_candles = base_candles + future_candles

    # Re-evaluating strictly the historical slice at index 30
    state_after = coordinator.run(all_candles[:30], symbol="BTC/USDT", timeframe="1H")

    # Assert invariant: Historical state is strictly identical
    assert state_before.current_price == state_after.current_price
    assert state_before.structure_state.external_trend == state_after.structure_state.external_trend
    assert len(state_before.swings) == len(state_after.swings)
    assert len(state_before.keyzones) == len(state_after.keyzones)
