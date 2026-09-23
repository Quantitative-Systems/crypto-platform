"""Crypto Trading Platform — Production Observability, Metrics & Telemetry.

Provides structured JSON logging, real-time latency tracking, health monitoring,
and system alert dispatch across all subsystems.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.events import SystemAlertEvent

logger = logging.getLogger("crypto_platform.observability")


@dataclass
class HealthStatus:
    subsystem: str
    status: str                         # HEALTHY, DEGRADED, CRITICAL
    message: str
    last_check_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    details: Dict[str, Any] = field(default_factory=dict)


class ObservabilityCollector:
    """Collects real-time operational telemetry, metrics, and health states."""

    def __init__(self):
        self._health_registry: Dict[str, HealthStatus] = {}
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._latencies_ms: Dict[str, List[float]] = {}
        self._alerts: List[SystemAlertEvent] = []

    def set_subsystem_health(
        self, subsystem: str, status: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        self._health_registry[subsystem] = HealthStatus(
            subsystem=subsystem,
            status=status.upper(),
            message=message,
            details=details or {},
        )

    def inc_counter(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def record_latency(self, metric_name: str, latency_ms: float) -> None:
        buf = self._latencies_ms.setdefault(metric_name, [])
        buf.append(latency_ms)
        if len(buf) > 1000:
            buf.pop(0)

    def trigger_alert(self, level: str, source: str, message: str, context: Optional[Dict[str, Any]] = None) -> SystemAlertEvent:
        alert = SystemAlertEvent(
            level=level.upper(),
            source=source,
            message=message,
            context=context or {},
        )
        self._alerts.append(alert)
        if level.upper() in ("CRITICAL", "EMERGENCY"):
            logger.critical(f"[{source}] {message} - Context: {context}")
        else:
            logger.warning(f"[{source}] {message}")
        return alert

    def get_system_health(self) -> Dict[str, Any]:
        """Aggregate health across all monitored planes."""
        overall_status = "HEALTHY"
        for h in self._health_registry.values():
            if h.status == "CRITICAL":
                overall_status = "CRITICAL"
                break
            elif h.status == "DEGRADED" and overall_status != "CRITICAL":
                overall_status = "DEGRADED"

        latency_summaries = {}
        for name, vals in self._latencies_ms.items():
            if vals:
                latency_summaries[name] = {
                    "avg_ms": round(sum(vals) / len(vals), 3),
                    "p95_ms": round(float(sorted(vals)[int(len(vals) * 0.95)]), 3),
                    "count": len(vals),
                }

        return {
            "overall_status": overall_status,
            "timestamp_ms": int(time.time() * 1000),
            "subsystems": {k: asdict(v) for k, v in self._health_registry.items()},
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "latencies": latency_summaries,
            "recent_alerts": [asdict(a) for a in self._alerts[-10:]],
        }
