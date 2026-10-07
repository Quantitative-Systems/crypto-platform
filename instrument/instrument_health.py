"""Instrument Health and Data Integrity Monitoring.

Ensures that before any decision or order execution occurs, the underlying
market data feed, exchange gateway, and orderbook integrity pass strict
health gates.

If data is degraded, stale, or corrupted, the system halts or transitions
to SAFE FLAT under the Data Health Governor.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class HealthStatus(str, Enum):
    """Operational health status of an instrument data feed."""
    HEALTHY = "HEALTHY"            # Full real-time feed, normal latency, valid ticks
    DEGRADED = "DEGRADED"          # Elevated latency or occasional dropped ticks
    STALE = "STALE"                # No tick within allowable threshold
    DISCONNECTED = "DISCONNECTED"  # Exchange WebSocket/REST feed down
    CORRUPTED = "CORRUPTED"        # Crossed book, inverted OHLC, or broken timestamps


@dataclass
class InstrumentHealth:
    """Real-time health report for a specific trading instrument."""
    symbol: str
    status: HealthStatus = HealthStatus.HEALTHY
    feed_alive: bool = True
    last_tick_time: float = field(default_factory=time.time)
    feed_latency_ms: float = 45.0
    max_tolerated_latency_ms: float = 1000.0  # 1.0 second max latency
    max_tick_staleness_sec: float = 15.0     # 15s without tick = stale
    gap_detected: bool = False
    ohlc_valid: bool = True
    orderbook_valid: bool = True
    spread_valid: bool = True
    clock_synced: bool = True
    active_issues: List[str] = field(default_factory=list)

    def evaluate(self, current_time: float | None = None) -> HealthStatus:
        """Evaluate real-time metrics and update health status."""
        now = current_time if current_time is not None else time.time()
        self.active_issues.clear()

        # Check staleness
        staleness = now - self.last_tick_time
        if staleness > self.max_tick_staleness_sec:
            self.feed_alive = False
            self.active_issues.append(f"Feed stale: {staleness:.1f}s since last tick (max {self.max_tick_staleness_sec}s)")

        # Check latency
        if self.feed_latency_ms > self.max_tolerated_latency_ms:
            self.active_issues.append(f"Latency {self.feed_latency_ms:.1f}ms exceeds {self.max_tolerated_latency_ms:.1f}ms")

        # Check data integrity
        if not self.ohlc_valid:
            self.active_issues.append("OHLC price integrity check failed (e.g., High < Low)")
        if not self.orderbook_valid:
            self.active_issues.append("Order book corrupted (e.g., Best Bid >= Best Ask)")
        if not self.spread_valid:
            self.active_issues.append("Spread integrity failed")
        if not self.clock_synced:
            self.active_issues.append("System clock desynchronized from exchange server clock")
        if self.gap_detected:
            self.active_issues.append("Sequence gap detected in trade/candle feed")

        # Determine overall status
        if not self.feed_alive or not self.clock_synced:
            self.status = HealthStatus.DISCONNECTED
        elif not self.ohlc_valid or not self.orderbook_valid or not self.spread_valid:
            self.status = HealthStatus.CORRUPTED
        elif staleness > self.max_tick_staleness_sec or self.gap_detected:
            self.status = HealthStatus.STALE
        elif self.feed_latency_ms > self.max_tolerated_latency_ms:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY

        return self.status

    def is_operational(self) -> bool:
        """Determines if instrument is safe for trading decisions."""
        return self.status == HealthStatus.HEALTHY
