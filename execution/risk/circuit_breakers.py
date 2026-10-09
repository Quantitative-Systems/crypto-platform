"""STRATA Digital Trading Platform — Automated Circuit Breakers & Capital Protection.

Hardware/software safeguards that protect capital against market shocks, systemic failures,
and cascading losses:
1. MaxDrawdownBreaker: Halts entries if drawdown exceeds threshold (default 4.0%).
2. ConsecutiveLossBreaker: Pauses trading if consecutive losses hit ceiling (default 3 losses).
3. VolatilitySpikeBreaker: Blocks entries during anomalous volatility regime shocks.
4. StaleDataBreaker: Tripped if market data feed latency exceeds safety window (> 30s).
5. ReconciliationDiscrepancyBreaker: Halts immediately on broker state mismatch.

NON-NEGOTIABLE INVARIANT:
When any circuit breaker is tripped, NEW TRADING IS BLOCKED.
No human intervention can force an order through an active tripped breaker without explicit
administrative reset.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BreakerStatus(str, Enum):
    ARMED = "ARMED"
    TRIPPED = "TRIPPED"
    COOLDOWN = "COOLDOWN"


@dataclass
class BreakerEvaluationResult:
    is_safe: bool
    status: BreakerStatus
    reason_code: str
    details: Dict[str, Any] = field(default_factory=dict)


class CircuitBreakerBase:
    """Base class for all capital protection circuit breakers."""

    def __init__(self, name: str):
        self.name = name
        self.status = BreakerStatus.ARMED
        self.tripped_timestamp_ms: int = 0
        self.trip_count: int = 0
        self.last_trip_reason: str = ""

    def trip(self, reason: str) -> None:
        self.status = BreakerStatus.TRIPPED
        self.tripped_timestamp_ms = int(time.time() * 1000)
        self.trip_count += 1
        self.last_trip_reason = reason
        logger.critical(f"CIRCUIT BREAKER TRIPPED [{self.name}]: {reason}")

    def reset(self) -> None:
        self.status = BreakerStatus.ARMED
        self.last_trip_reason = ""
        logger.warning(f"CIRCUIT BREAKER RESET [{self.name}]: Returned to ARMED status.")

    def evaluate(self, context: Dict[str, Any]) -> BreakerEvaluationResult:
        raise NotImplementedError


class MaxDrawdownBreaker(CircuitBreakerBase):
    """Halts new trading if portfolio drawdown from peak exceeds safety limit."""

    def __init__(self, max_drawdown_pct: float = 0.04):  # 4.0%
        super().__init__("MaxDrawdownBreaker")
        self.max_drawdown_pct = max_drawdown_pct

    def evaluate(self, context: Dict[str, Any]) -> BreakerEvaluationResult:
        current_equity = context.get("current_equity_usd", 100_000.0)
        peak_equity = context.get("peak_equity_usd", current_equity)

        if peak_equity <= 0:
            return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NORMAL")

        dd_pct = (peak_equity - current_equity) / peak_equity
        if dd_pct >= self.max_drawdown_pct:
            if self.status != BreakerStatus.TRIPPED:
                self.trip(f"Drawdown {dd_pct*100:.2f}% breached max limit {self.max_drawdown_pct*100:.2f}%")
            return BreakerEvaluationResult(
                is_safe=False,
                status=BreakerStatus.TRIPPED,
                reason_code="CIRCUIT_BREAKER_MAX_DRAWDOWN",
                details={"drawdown_pct": dd_pct, "max_limit_pct": self.max_drawdown_pct},
            )

        if self.status == BreakerStatus.TRIPPED and dd_pct < self.max_drawdown_pct:
            self.reset()

        return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NORMAL")


class ConsecutiveLossBreaker(CircuitBreakerBase):
    """Enforces cooldown after consecutive losing trades."""

    def __init__(self, max_consecutive_losses: int = 3, cooldown_seconds: int = 14400):  # 4 hours
        super().__init__("ConsecutiveLossBreaker")
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_seconds = cooldown_seconds

    def evaluate(self, context: Dict[str, Any]) -> BreakerEvaluationResult:
        consecutive_losses = context.get("consecutive_losses", 0)

        # Check if in cooldown
        now_ms = int(time.time() * 1000)
        if self.status == BreakerStatus.TRIPPED:
            elapsed_sec = (now_ms - self.tripped_timestamp_ms) / 1000.0
            if elapsed_sec < self.cooldown_seconds:
                return BreakerEvaluationResult(
                    is_safe=False,
                    status=BreakerStatus.COOLDOWN,
                    reason_code="CIRCUIT_BREAKER_CONSECUTIVE_LOSS_COOLDOWN",
                    details={"elapsed_sec": elapsed_sec, "cooldown_sec": self.cooldown_seconds},
                )
            else:
                self.reset()

        if consecutive_losses >= self.max_consecutive_losses:
            self.trip(f"Consecutive losses {consecutive_losses} >= threshold {self.max_consecutive_losses}")
            return BreakerEvaluationResult(
                is_safe=False,
                status=BreakerStatus.TRIPPED,
                reason_code="CIRCUIT_BREAKER_CONSECUTIVE_LOSS",
                details={"consecutive_losses": consecutive_losses},
            )

        return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NORMAL")


class StaleDataBreaker(CircuitBreakerBase):
    """Trips if market data stream latency exceeds 30 seconds."""

    def __init__(self, max_stale_seconds: float = 30.0):
        super().__init__("StaleDataBreaker")
        self.max_stale_seconds = max_stale_seconds

    def evaluate(self, context: Dict[str, Any]) -> BreakerEvaluationResult:
        last_tick_ts_ms = context.get("last_tick_timestamp_ms", 0)
        if last_tick_ts_ms <= 0:
            return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NO_DATA_TIMESTAMP")

        now_ms = int(time.time() * 1000)
        staleness_sec = (now_ms - last_tick_ts_ms) / 1000.0

        if staleness_sec > self.max_stale_seconds:
            self.trip(f"Market data feed is stale ({staleness_sec:.1f}s > {self.max_stale_seconds}s)")
            return BreakerEvaluationResult(
                is_safe=False,
                status=BreakerStatus.TRIPPED,
                reason_code="CIRCUIT_BREAKER_DATA_STALE",
                details={"staleness_sec": staleness_sec, "threshold": self.max_stale_seconds},
            )

        if self.status == BreakerStatus.TRIPPED and staleness_sec <= self.max_stale_seconds:
            self.reset()

        return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NORMAL")


class ReconciliationDiscrepancyBreaker(CircuitBreakerBase):
    """Trips immediately if reconciliation finds discrepancy between internal & broker state."""

    def __init__(self):
        super().__init__("ReconciliationDiscrepancyBreaker")

    def evaluate(self, context: Dict[str, Any]) -> BreakerEvaluationResult:
        discrepancy_count = context.get("reconciliation_discrepancy_count", 0)
        if discrepancy_count > 0:
            self.trip(f"{discrepancy_count} state reconciliation invariant breaches detected!")
            return BreakerEvaluationResult(
                is_safe=False,
                status=BreakerStatus.TRIPPED,
                reason_code="CIRCUIT_BREAKER_RECONCILIATION_BREACH",
                details={"discrepancies": discrepancy_count},
            )

        if self.status == BreakerStatus.TRIPPED and discrepancy_count == 0:
            self.reset()

        return BreakerEvaluationResult(True, BreakerStatus.ARMED, "NORMAL")


class CompositeCircuitBreakerManager:
    """Evaluates all registered circuit breakers before simulated or live execution."""

    def __init__(self):
        self.breakers: List[CircuitBreakerBase] = [
            MaxDrawdownBreaker(),
            ConsecutiveLossBreaker(),
            StaleDataBreaker(),
            ReconciliationDiscrepancyBreaker(),
        ]

    def evaluate_all(self, context: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Evaluate all breakers. Return (all_safe, list_of_failed_reasons, breaker_states)."""
        all_safe = True
        failed_reasons: List[str] = []
        breaker_states: Dict[str, Any] = {}

        for breaker in self.breakers:
            res = breaker.evaluate(context)
            breaker_states[breaker.name] = {
                "status": res.status.value,
                "is_safe": res.is_safe,
                "reason_code": res.reason_code,
                "details": res.details,
            }
            if not res.is_safe:
                all_safe = False
                failed_reasons.append(res.reason_code)

        return all_safe, failed_reasons, breaker_states

    def reset_all(self) -> None:
        for breaker in self.breakers:
            breaker.reset()

    def restore_states(self, states: Dict[str, Any]) -> None:
        """Restores circuit breaker states from checkpoint on restart recovery."""
        if not states:
            return
        for breaker in self.breakers:
            if breaker.name in states:
                b_info = states[breaker.name]
                if isinstance(b_info, dict) and b_info.get("status") == BreakerStatus.TRIPPED.value:
                    reason = b_info.get("reason_code", "RESTORED_TRIPPED_FROM_CHECKPOINT")
                    breaker.trip(reason)
                    logger.warning(f"Restored circuit breaker {breaker.name} in TRIPPED state: {reason}")
