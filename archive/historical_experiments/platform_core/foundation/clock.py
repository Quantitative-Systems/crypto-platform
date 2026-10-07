"""
Quantitative Crypto Platform (QCP) — Unified Clock Management.

Provides high-resolution monotonic time, UTC timestamps, simulation clock time,
and clock drift detection.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional


class PlatformClock:
    """
    Unified timekeeper supporting both real-time operational execution and
    historical backtest/simulation replay.
    """

    def __init__(self, is_simulated: bool = False, initial_sim_time: int = 0):
        self._is_simulated = is_simulated
        self._sim_time_sec = initial_sim_time

    @property
    def is_simulated(self) -> bool:
        return self._is_simulated

    def now_utc_sec(self) -> int:
        if self._is_simulated:
            return self._sim_time_sec
        return int(time.time())

    def now_utc_ms(self) -> int:
        if self._is_simulated:
            return self._sim_time_sec * 1000
        return int(time.time() * 1000)

    def now_utc_ns(self) -> int:
        if self._is_simulated:
            return self._sim_time_sec * 1_000_000_000
        return time.time_ns()

    def now_iso(self) -> str:
        dt = datetime.fromtimestamp(self.now_utc_sec(), tz=timezone.utc)
        return dt.isoformat()

    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def set_simulation_time(self, timestamp_sec: int) -> None:
        if not self._is_simulated:
            raise RuntimeError("Cannot set simulation time on a non-simulated real-time clock.")
        if timestamp_sec < self._sim_time_sec:
            raise ValueError(f"Clock invariant violated: time cannot move backward ({timestamp_sec} < {self._sim_time_sec})")
        self._sim_time_sec = timestamp_sec

    def advance_simulation_time(self, delta_sec: int) -> None:
        if delta_sec < 0:
            raise ValueError("Time delta cannot be negative.")
        self._sim_time_sec += delta_sec

    def measure_clock_drift_sec(self, external_reference_sec: float) -> float:
        """Computes drift between local wall clock and exchange server reference."""
        local = time.time()
        return local - external_reference_sec


class SystemClock:
    """Convenience system clock wrapper for operational UTC and epoch timing."""

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def now_epoch_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

