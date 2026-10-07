"""Event Clock: Multi-Resolution Temporal Proximity & Catalyst Management.

Provides continuous temporal awareness relative to scheduled macroeconomic catalysts,
monetary policy decisions, and crypto-native structural events.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from market_intelligence.events.contracts import (
    CausalEvent,
    EventClockPhase,
    EventImportance,
    EventTimeContext,
)

MS_IN_MINUTE = 60 * 1000
MS_IN_HOUR = 60 * MS_IN_MINUTE
MS_IN_DAY = 24 * MS_IN_HOUR


class EventClock:
    """Evaluates temporal distance to catalysts and derives risk-gating invariants."""

    def __init__(
        self,
        events: Optional[List[CausalEvent]] = None,
        freeze_window_pre_ms: int = 15 * MS_IN_MINUTE,  # T-15m
        freeze_window_post_ms: int = 15 * MS_IN_MINUTE, # T+15m
    ):
        self.events = sorted(events or [], key=lambda e: e.timestamp_ms)
        self.freeze_window_pre_ms = freeze_window_pre_ms
        self.freeze_window_post_ms = freeze_window_post_ms

    def register_event(self, event: CausalEvent) -> None:
        """Register a causal event maintaining chronological sort order."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp_ms)

    def evaluate_context(
        self,
        current_time_ms: int,
        symbol: Optional[str] = None,
        min_importance: EventImportance = EventImportance.HIGH,
    ) -> EventTimeContext:
        """Evaluate the temporal context at timestamp t for an asset."""
        # Filter relevant events matching symbol and minimum importance threshold
        importance_rank = {
            EventImportance.LOW: 1,
            EventImportance.MEDIUM: 2,
            EventImportance.HIGH: 3,
            EventImportance.CRITICAL: 4,
        }
        target_rank = importance_rank.get(min_importance, 3)

        relevant_events = [
            e for e in self.events
            if importance_rank.get(e.importance, 1) >= target_rank
            and (not symbol or not e.affected_assets or symbol in e.affected_assets or "ALL" in e.affected_assets)
        ]

        # Find nearest upcoming event (timestamp >= current_time_ms)
        upcoming = [e for e in relevant_events if e.timestamp_ms >= current_time_ms]
        nearest_upcoming: Optional[CausalEvent] = upcoming[0] if upcoming else None

        # Find nearest past event (timestamp < current_time_ms)
        past = [e for e in relevant_events if e.timestamp_ms < current_time_ms]
        nearest_past: Optional[CausalEvent] = past[-1] if past else None

        time_to_upcoming_ms = (
            nearest_upcoming.timestamp_ms - current_time_ms if nearest_upcoming else None
        )
        time_since_past_ms = (
            current_time_ms - nearest_past.timestamp_ms if nearest_past else None
        )

        # Determine Clock Phase
        clock_phase = EventClockPhase.FAR_PRE_EVENT
        is_trading_prohibited = False
        is_compression_expected = False
        is_volatility_expansion_expected = False
        reason = "Normal market regime; no immediate catalyst proximity."

        # Check proximity to past event
        if time_since_past_ms is not None and time_since_past_ms <= 15 * MS_IN_MINUTE:
            clock_phase = EventClockPhase.AT_EVENT
            is_trading_prohibited = True
            is_volatility_expansion_expected = True
            reason = f"Within post-event volatility window (+{time_since_past_ms // MS_IN_MINUTE}m) of {nearest_past.event_name}."
        elif time_since_past_ms is not None and time_since_past_ms <= 1 * MS_IN_HOUR:
            clock_phase = EventClockPhase.T_PLUS_15M
            reason = f"Initial price discovery phase (+{time_since_past_ms // MS_IN_MINUTE}m) after {nearest_past.event_name}."
        elif time_since_past_ms is not None and time_since_past_ms <= 4 * MS_IN_HOUR:
            clock_phase = EventClockPhase.T_PLUS_1H
            reason = f"Structural validation phase (+{time_since_past_ms // MS_IN_HOUR}h) after {nearest_past.event_name}."
        elif time_since_past_ms is not None and time_since_past_ms <= 24 * MS_IN_HOUR:
            clock_phase = EventClockPhase.T_PLUS_4H
            reason = f"Equilibrium consolidation phase after {nearest_past.event_name}."

        # Upcoming event overrides / refines pre-event phases if closer
        if time_to_upcoming_ms is not None:
            if time_to_upcoming_ms <= self.freeze_window_pre_ms:
                clock_phase = EventClockPhase.T_MINUS_15M
                is_trading_prohibited = True
                is_volatility_expansion_expected = True
                reason = f"High-risk freeze window: {time_to_upcoming_ms // MS_IN_MINUTE}m prior to {nearest_upcoming.event_name}."
            elif time_to_upcoming_ms <= 1 * MS_IN_HOUR:
                clock_phase = EventClockPhase.T_MINUS_1H
                is_compression_expected = True
                reason = f"Pre-catalyst compression window: {time_to_upcoming_ms // MS_IN_MINUTE}m prior to {nearest_upcoming.event_name}."
            elif time_to_upcoming_ms <= 4 * MS_IN_HOUR:
                clock_phase = EventClockPhase.T_MINUS_4H
                is_compression_expected = True
                reason = f"Pre-catalyst de-risking: {time_to_upcoming_ms // MS_IN_HOUR}h prior to {nearest_upcoming.event_name}."
            elif time_to_upcoming_ms <= 24 * MS_IN_HOUR:
                clock_phase = EventClockPhase.T_MINUS_24H
                reason = f"Advance event awareness: {time_to_upcoming_ms // MS_IN_HOUR}h prior to {nearest_upcoming.event_name}."

        return EventTimeContext(
            current_time_ms=current_time_ms,
            clock_phase=clock_phase,
            nearest_upcoming_event=nearest_upcoming,
            time_to_upcoming_ms=time_to_upcoming_ms,
            nearest_past_event=nearest_past,
            time_since_past_ms=time_since_past_ms,
            is_trading_prohibited=is_trading_prohibited,
            is_compression_expected=is_compression_expected,
            is_volatility_expansion_expected=is_volatility_expansion_expected,
            reason=reason,
        )
