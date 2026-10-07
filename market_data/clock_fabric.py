"""Deterministic Clock and Canonical Event Fabric.

Implements the institutional clock architecture for 24/7/365 operations:
- Every event has immutable provenance:
  event_id, event_time, received_time, processed_time, source_time,
  source, symbol, data_type, revision, quality
- Strictly enforces the causal availability invariant:
  Information is ONLY available at decision time if received_time <= decision_time.
  Zero lookahead leakage.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataQuality(str, Enum):
    """Quality certification of incoming data."""
    PRISTINE = "PRISTINE"          # Directly received from authoritative exchange WebSocket
    INTERPOLATED = "INTERPOLATED"  # Gap-filled or sampled
    SUSPECT = "SUSPECT"            # Outlier or potential bad print
    STALE = "STALE"                # Delayed arrival


class DataType(str, Enum):
    """Canonical data categories."""
    OHLCV = "OHLCV"
    TRADES = "TRADES"
    ORDER_BOOK = "ORDER_BOOK"
    FUNDING_RATE = "FUNDING_RATE"
    OPEN_INTEREST = "OPEN_INTEREST"
    LIQUIDATIONS = "LIQUIDATIONS"
    MACRO_EVENT = "MACRO_EVENT"
    CROSS_MARKET = "CROSS_MARKET"
    EXECUTION_FILL = "EXECUTION_FILL"


@dataclass(frozen=True)
class CanonicalEvent:
    """Standardized event packet across market, macro, and execution channels."""
    event_id: str
    event_time: float          # Time event occurred at source (UTC epoch sec)
    received_time: float       # Time event arrived at local engine gateway
    processed_time: float      # Time event was parsed and committed to fabric
    source_time: float         # Raw exchange timestamp
    source: str                # e.g., "BINANCE", "COINBASE", "FRED_MACRO"
    symbol: str                # Canonical symbol e.g., "BTC/USDT", "BTC/XAU"
    data_type: DataType        # Canonical data category
    payload: Dict[str, Any]    # Event payload (e.g. OHLCV dict, L2 book, macro print)
    revision: int = 1          # 1 for original, >1 for restatements/revisions
    quality: DataQuality = DataQuality.PRISTINE

    def is_causally_available_at(self, decision_time: float) -> bool:
        """Enforces causal invariant: decision_time must be >= received_time."""
        return self.received_time <= decision_time


def create_canonical_event(
    event_time: float,
    source: str,
    symbol: str,
    data_type: DataType,
    payload: Dict[str, Any],
    received_time: Optional[float] = None,
    source_time: Optional[float] = None,
    quality: DataQuality = DataQuality.PRISTINE,
) -> CanonicalEvent:
    """Helper factory for building verified canonical events."""
    now = time.time()
    rcv = received_time if received_time is not None else now
    src_t = source_time if source_time is not None else event_time

    return CanonicalEvent(
        event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
        event_time=event_time,
        received_time=rcv,
        processed_time=now,
        source_time=src_t,
        source=source,
        symbol=symbol,
        data_type=data_type,
        payload=payload,
        revision=1,
        quality=quality,
    )


class DeterministicClock:
    """Institutional system clock enforcing causal replay and live time invariants."""

    def __init__(self, initial_time: Optional[float] = None, max_drift_tolerance_ms: float = 250.0):
        self._current_time: float = initial_time if initial_time is not None else time.time()
        self.max_drift_tolerance_ms = max_drift_tolerance_ms

    @property
    def current_time(self) -> float:
        return self._current_time

    def set_time(self, timestamp: float) -> None:
        """Advance time in deterministic replay or simulation."""
        if timestamp < self._current_time:
            raise ValueError(f"Clock cannot move backwards: new {timestamp} < current {self._current_time}")
        self._current_time = timestamp

    def advance_by(self, delta_seconds: float) -> None:
        """Advance clock by relative offset."""
        if delta_seconds < 0:
            raise ValueError("Time delta cannot be negative")
        self._current_time += delta_seconds

    def is_causally_visible(self, event: CanonicalEvent) -> bool:
        """Check if event is visible at current clock time."""
        return event.received_time <= self._current_time

    def filter_visible_events(self, events: List[CanonicalEvent]) -> List[CanonicalEvent]:
        """Filter event stream to strictly causally available subset."""
        return [e for e in events if self.is_causally_visible(e)]

    def verify_clock_synchronization(self, external_server_time: float) -> Tuple[bool, float]:
        """Verify synchronization against exchange server time."""
        drift_ms = abs(self._current_time - external_server_time) * 1000.0
        synced = drift_ms <= self.max_drift_tolerance_ms
        return synced, drift_ms
