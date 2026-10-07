"""Causal Event Engine: Ingestion, Surprise Decomposition, and Impact Transmission.

Processes raw economic calendar prints, on-chain flows, central bank announcements,
and cross-market shocks into normalized, causal representations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from market_intelligence.events.contracts import (
    CausalEvent,
    EventCategory,
    EventImportance,
    EventSurprise,
    EventTimeContext,
    SurpriseDirection,
    TransmissionChain,
)
from market_intelligence.events.event_clock import EventClock


class CausalEventEngine:
    """Core engine for managing causal event information and transmission hypotheses."""

    def __init__(self, event_clock: Optional[EventClock] = None):
        self.events: List[CausalEvent] = []
        self.clock = event_clock or EventClock()
        self._events_by_id: Dict[str, CausalEvent] = {}

    def register_event(
        self,
        event_id: str,
        event_name: str,
        category: EventCategory,
        importance: EventImportance,
        timestamp_ms: int,
        actual: float,
        expected: Optional[float] = None,
        previous: Optional[float] = None,
        revision: Optional[float] = None,
        unit: str = "%",
        affected_assets: Optional[List[str]] = None,
        headline: str = "",
        transmission: Optional[TransmissionChain] = None,
        source: str = "OFFICIAL",
        meta: Optional[Dict[str, Any]] = None,
    ) -> CausalEvent:
        """Register an event with calculated surprise metrics."""
        surprise = EventSurprise(
            actual=actual,
            expected=expected,
            previous=previous,
            revision=revision,
            unit=unit,
        )

        event = CausalEvent(
            event_id=event_id,
            event_name=event_name,
            category=category,
            importance=importance,
            timestamp_ms=timestamp_ms,
            surprise=surprise,
            affected_assets=affected_assets or ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            transmission=transmission,
            headline=headline,
            source=source,
            meta=meta or {},
        )

        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp_ms)
        self._events_by_id[event_id] = event
        self.clock.register_event(event)
        return event

    def load_events_from_records(self, records: List[Dict[str, Any]]) -> int:
        """Bulk load events from serializable dictionaries."""
        count = 0
        for rec in records:
            category = EventCategory(rec.get("category", "MACROECONOMIC"))
            importance = EventImportance(rec.get("importance", "MEDIUM"))
            transmission_data = rec.get("transmission")
            transmission = None
            if transmission_data:
                transmission = TransmissionChain(
                    primary_channel=transmission_data.get("primary_channel", ""),
                    secondary_channel=transmission_data.get("secondary_channel", ""),
                    tertiary_channel=transmission_data.get("tertiary_channel", ""),
                    affected_assets=transmission_data.get("affected_assets", []),
                    expected_market_response=transmission_data.get("expected_market_response", ""),
                    historical_hit_rate=transmission_data.get("historical_hit_rate", 0.5),
                )

            self.register_event(
                event_id=rec["event_id"],
                event_name=rec["event_name"],
                category=category,
                importance=importance,
                timestamp_ms=rec["timestamp_ms"],
                actual=rec["actual"],
                expected=rec.get("expected"),
                previous=rec.get("previous"),
                revision=rec.get("revision"),
                unit=rec.get("unit", "%"),
                affected_assets=rec.get("affected_assets"),
                headline=rec.get("headline", ""),
                transmission=transmission,
                source=rec.get("source", "OFFICIAL"),
                meta=rec.get("meta", {}),
            )
            count += 1
        return count

    def get_latest_event_prior_to(
        self,
        timestamp_ms: int,
        category: Optional[EventCategory] = None,
        symbol: Optional[str] = None,
    ) -> Optional[CausalEvent]:
        """Strict causal query: retrieves the most recent event published at or before timestamp_ms."""
        candidates = [
            e for e in self.events
            if e.timestamp_ms <= timestamp_ms
            and (category is None or e.category == category)
            and (symbol is None or not e.affected_assets or symbol in e.affected_assets or "ALL" in e.affected_assets)
        ]
        return candidates[-1] if candidates else None

    def get_events_in_range(
        self,
        start_ms: int,
        end_ms: int,
        category: Optional[EventCategory] = None,
    ) -> List[CausalEvent]:
        """Retrieve all events within a temporal bounding interval."""
        return [
            e for e in self.events
            if start_ms <= e.timestamp_ms <= end_ms
            and (category is None or e.category == category)
        ]

    def evaluate_clock_context(
        self,
        current_time_ms: int,
        symbol: Optional[str] = None,
        min_importance: EventImportance = EventImportance.HIGH,
    ) -> EventTimeContext:
        """Delegate temporal proximity evaluation to the EventClock."""
        return self.clock.evaluate_context(current_time_ms, symbol=symbol, min_importance=min_importance)
