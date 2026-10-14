"""Unit tests for STRATA Phase 4: Point-in-Time News and Macro Narrative Intelligence."""
from __future__ import annotations

import pytest
import numpy as np

from market_model.news_narrative_intelligence import (
    EventCategory,
    EventImpactLevel,
    NarrativeRegime,
    PointInTimeMacroEvent,
    PointInTimeNewsCalendar,
    build_canonical_crypto_macro_calendar,
)


def test_causal_invariant_enforces_no_lookahead():
    """Asserts that an event with knowledge_time < actual_release_time raises ValueError."""
    with pytest.raises(ValueError, match="Causal lookahead violation"):
        PointInTimeMacroEvent(
            event_id="TEST_TIME_TRAVEL",
            event_name="Time Traveler Release",
            category=EventCategory.MACRO_ECONOMY,
            impact=EventImpactLevel.HIGH,
            scheduled_time_ms=1000,
            actual_release_time_ms=2000,
            knowledge_time_ms=1500,  # Lookahead violation!
        )


def test_point_in_time_visibility_boundary():
    """Asserts that events are invisible prior to knowledge_time and visible after."""
    evt = PointInTimeMacroEvent(
        event_id="TEST_CPI",
        event_name="US CPI YoY",
        category=EventCategory.MACRO_ECONOMY,
        impact=EventImpactLevel.HIGH,
        scheduled_time_ms=1700000000000,
        actual_release_time_ms=1700000001000,
        knowledge_time_ms=1700000002000,
    )

    # 1ms before knowledge_time -> strictly invisible
    assert not evt.is_visible_at(1700000001999)
    # Exactly at knowledge_time -> visible
    assert evt.is_visible_at(1700000002000)
    # After knowledge_time -> visible
    assert evt.is_visible_at(1700000005000)


def test_protective_volatility_window():
    """Asserts that the protective entry freeze window covers pre-event and post-event intervals."""
    evt_ts = 1_000_000_000
    pre_ms = 30 * 60 * 1000   # 30m
    post_ms = 60 * 60 * 1000  # 60m

    evt = PointInTimeMacroEvent(
        event_id="TEST_FOMC",
        event_name="FOMC Decision",
        category=EventCategory.CENTRAL_BANK,
        impact=EventImpactLevel.HIGH,
        scheduled_time_ms=evt_ts,
        actual_release_time_ms=evt_ts,
        knowledge_time_ms=evt_ts + 1000,
        pre_event_freeze_ms=pre_ms,
        post_event_freeze_ms=post_ms,
    )

    # 31 minutes before release -> outside protective window
    assert not evt.is_in_protective_window(evt_ts - pre_ms - 1)
    # 29 minutes before release -> inside protective window (Freeze)
    assert evt.is_in_protective_window(evt_ts - pre_ms + 1000)
    # At exact release time -> inside protective window
    assert evt.is_in_protective_window(evt_ts)
    # 59 minutes after release -> inside protective window (Freeze)
    assert evt.is_in_protective_window(evt_ts + post_ms - 1000)
    # 61 minutes after release -> outside protective window (Safe)
    assert not evt.is_in_protective_window(evt_ts + post_ms + 1)


def test_calendar_active_event_query():
    """Asserts that PointInTimeNewsCalendar returns the active high-impact event during its window."""
    cal = build_canonical_crypto_macro_calendar()

    # Query during the 2024 Bitcoin Halving window (Halving ts: 1713571740000)
    halving_ts = 1713571740000
    active = cal.get_active_event_window(halving_ts)
    assert active is not None
    assert active.event_id == "BTC_HALVING_2024"
    assert active.impact == EventImpactLevel.HIGH

    # Query 10 days after Halving -> no active event window
    assert cal.get_active_event_window(halving_ts + 10 * 86400 * 1000) is None


def test_measure_event_volatility_impact():
    """Asserts that empirical range expansion is correctly measured around an event bar."""
    cal = PointInTimeNewsCalendar()
    evt_ts = 100_000_000

    evt = PointInTimeMacroEvent(
        event_id="TEST_EXPANSION",
        event_name="Major CPI Shock",
        category=EventCategory.MACRO_ECONOMY,
        impact=EventImpactLevel.HIGH,
        scheduled_time_ms=evt_ts,
        actual_release_time_ms=evt_ts,
        knowledge_time_ms=evt_ts,
    )
    cal.register_event(evt)

    # Construct synthetic candles around event
    n_bars = 40
    timestamps = np.arange(evt_ts - 20 * 3600 * 1000, evt_ts + 20 * 3600 * 1000, 3600 * 1000)
    opens = np.full(n_bars, 50000.0)
    closes = np.full(n_bars, 50000.0)
    # Baseline range is 100
    highs = np.full(n_bars, 50050.0)
    lows = np.full(n_bars, 49950.0)

    # Event bar (index 20) experiences a 4x range expansion (range = 400)
    event_idx = int(np.searchsorted(timestamps, evt_ts, side="left"))
    highs[event_idx] = 50200.0
    lows[event_idx] = 49800.0
    closes[event_idx] = 50150.0

    impact_res = cal.measure_event_volatility_impact(
        event=evt,
        timestamps_ms=timestamps,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        lookback_bars=10,
        forward_bars=10,
    )

    assert impact_res["status"] != "INSUFFICIENT_DATA_SURROUNDING_EVENT"
    assert impact_res["pre_mean_range"] == 100.0
    assert impact_res["event_bar_range"] == 400.0
    assert impact_res["event_range_expansion_x"] == 4.0
    assert impact_res["high_volatility_confirmed"] is True
