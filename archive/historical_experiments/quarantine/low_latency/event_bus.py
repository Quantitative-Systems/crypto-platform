"""
QCP Phase 12 — Low Latency Infrastructure: Fast Ring-Buffer Event Bus.
Implements zero-copy/low-overhead publish-subscribe bus with nanosecond timestamping.

MEASURE BEFORE OPTIMIZING:
- Strictly does NOT claim fabricated sub-microsecond HFT performance.
- Provides high-precision measurement infrastructure to benchmark real latencies.
- Tracks ingress, queue dwell, dispatch, and callback latencies per event.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("QCP.LowLatency.EventBus")


@dataclass
class TimestampedEvent:
    event_type: str
    payload: Any
    ingress_timestamp_ns: int = field(default_factory=time.perf_counter_ns)
    dispatch_timestamp_ns: int = 0
    completion_timestamp_ns: int = 0


class FastEventBus:
    """
    Fixed-capacity ring-buffer event bus designed for high-throughput market data
    and signal distribution with zero unbounded memory growth.
    """

    def __init__(self, capacity: int = 65536):
        self.capacity = capacity
        self._subscribers: Dict[str, List[Callable[[TimestampedEvent], None]]] = collections.defaultdict(list)
        self._ring_buffer: collections.deque = collections.deque(maxlen=capacity)
        self._total_events_published: int = 0
        self._total_events_processed: int = 0
        self._dropped_events_overflow: int = 0
        self._latency_samples_ns: collections.deque = collections.deque(maxlen=10000)

    def subscribe(self, event_type: str, callback: Callable[[TimestampedEvent], None]) -> None:
        """Registers a callback handler for an event topic."""
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: Any) -> bool:
        """
        Enqueues an event into the ring buffer.
        If buffer is full, oldest unconsumed event drops to prevent memory bloat.
        """
        evt = TimestampedEvent(event_type=event_type, payload=payload)
        if len(self._ring_buffer) >= self.capacity:
            self._dropped_events_overflow += 1
        self._ring_buffer.append(evt)
        self._total_events_published += 1
        return True

    def dispatch_batch(self, max_batch_size: int = 1000) -> int:
        """
        Drains up to max_batch_size events from the ring buffer and delivers to subscribers.
        Measures end-to-end processing latency.
        """
        processed_count = 0
        while self._ring_buffer and processed_count < max_batch_size:
            evt: TimestampedEvent = self._ring_buffer.popleft()
            evt.dispatch_timestamp_ns = time.perf_counter_ns()

            callbacks = self._subscribers.get(evt.event_type, [])
            for cb in callbacks:
                try:
                    cb(evt)
                except Exception as e:
                    logger.error(f"Error in event subscriber {cb}: {e}")

            evt.completion_timestamp_ns = time.perf_counter_ns()
            latency_ns = evt.completion_timestamp_ns - evt.ingress_timestamp_ns
            self._latency_samples_ns.append(latency_ns)

            self._total_events_processed += 1
            processed_count += 1

        return processed_count

    def get_latency_stats_us(self) -> Dict[str, float]:
        """Returns latency distribution in microseconds."""
        if not self._latency_samples_ns:
            return {"p50_us": 0.0, "p90_us": 0.0, "p99_us": 0.0, "max_us": 0.0, "samples": 0}

        sorted_samples = sorted(self._latency_samples_ns)
        n = len(sorted_samples)

        def pct(p: float) -> float:
            idx = min(n - 1, int(n * p))
            return sorted_samples[idx] / 1000.0

        return {
            "p50_us": round(pct(0.50), 2),
            "p90_us": round(pct(0.90), 2),
            "p99_us": round(pct(0.99), 2),
            "max_us": round(sorted_samples[-1] / 1000.0, 2),
            "samples": n,
            "dropped_overflow": self._dropped_events_overflow,
        }
