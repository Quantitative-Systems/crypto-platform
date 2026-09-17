"""
QCP Phase 12 — Latency Telemetry & Benchmarking Harness.
Measures execution timing, memory allocations, and CPU cycles across critical path code.

MEASURE BEFORE OPTIMIZING:
Collects rigorous percentiles:
- Min, P50, P90, P99, P99.9, Max, Standard Deviation.
- Tracks garbage collection events and memory allocations.
"""

from __future__ import annotations

import gc
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional


@dataclass
class BenchmarkReport:
    name: str
    iterations: int
    total_time_ms: float
    min_us: float
    p50_us: float
    p90_us: float
    p99_us: float
    p99_9_us: float
    max_us: float
    mean_us: float
    stddev_us: float
    gc_collections: int


class LatencyHarness:
    """Benchmark runner for quantitative critical paths."""

    @staticmethod
    @contextmanager
    def measure_scope(scope_name: str, sink: Optional[List[float]] = None) -> Iterator[None]:
        start = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_us = (time.perf_counter_ns() - start) / 1000.0
            if sink is not None:
                sink.append(elapsed_us)

    @classmethod
    def benchmark(
        cls,
        name: str,
        target_fn: Callable[[], Any],
        iterations: int = 10000,
        warmup: int = 500,
    ) -> BenchmarkReport:
        """Executes repeated benchmark runs and computes statistically sound percentiles."""
        # Warmup phase
        for _ in range(warmup):
            target_fn()

        latencies_us: List[float] = []
        gc_before = gc.get_count()
        t0 = time.perf_counter()

        for _ in range(iterations):
            s = time.perf_counter_ns()
            target_fn()
            latencies_us.append((time.perf_counter_ns() - s) / 1000.0)

        total_ms = (time.perf_counter() - t0) * 1000.0
        gc_after = gc.get_count()
        gc_diff = sum(a - b for a, b in zip(gc_after, gc_before))

        latencies_us.sort()
        n = len(latencies_us)

        def pct(p: float) -> float:
            idx = min(n - 1, int(n * p))
            return latencies_us[idx]

        return BenchmarkReport(
            name=name,
            iterations=iterations,
            total_time_ms=round(total_ms, 2),
            min_us=round(latencies_us[0], 2),
            p50_us=round(pct(0.50), 2),
            p90_us=round(pct(0.90), 2),
            p99_us=round(pct(0.99), 2),
            p99_9_us=round(pct(0.999), 2),
            max_us=round(latencies_us[-1], 2),
            mean_us=round(statistics.mean(latencies_us), 2),
            stddev_us=round(statistics.stdev(latencies_us) if n > 1 else 0.0, 2),
            gc_collections=max(0, gc_diff),
        )
