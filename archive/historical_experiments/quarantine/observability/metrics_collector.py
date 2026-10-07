"""
Quantitative Crypto Platform (QCP) — Unified Observability & Telemetry Exporter.

Tracks metrics, trace spans, service heartbeats, execution quality, and alerts.
Outputs Prometheus-compatible exposition formats.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AlertRecord:
    alert_id: str
    severity: str  # INFO, WARNING, CRITICAL, PANIC
    subsystem: str
    message: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetricsCollector:
    """
    In-memory Prometheus-compatible metrics registry and health observer.
    """

    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._alerts: List[AlertRecord] = []
        self._init_standard_metrics()

    def _init_standard_metrics(self) -> None:
        self.set_gauge("qcp_capital_firewall_locked", 1.0)
        self.set_gauge("qcp_live_capital_usd", 0.0)
        self.set_gauge("qcp_portfolio_heat_pct", 0.0)
        self.set_counter("qcp_simulated_orders_total", 0.0)
        self.set_counter("qcp_risk_vetoes_total", 0.0)

    def inc_counter(self, name: str, value: float = 1.0) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe_histogram(self, name: str, value: float) -> None:
        self._histograms.setdefault(name, []).append(value)

    def emit_alert(self, severity: str, subsystem: str, message: str) -> AlertRecord:
        alt = AlertRecord(
            alert_id=f"alt_{int(time.time()*1000)}",
            severity=severity,
            subsystem=subsystem,
            message=message,
        )
        self._alerts.append(alt)
        return alt

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [a.__dict__ for a in self._alerts[-limit:]]

    def export_prometheus_format(self) -> str:
        """Emits standard Prometheus text exposition format."""
        lines = []
        for k, v in sorted(self._counters.items()):
            lines.append(f"# TYPE {k} counter")
            lines.append(f"{k} {v}")
        for k, v in sorted(self._gauges.items()):
            lines.append(f"# TYPE {k} gauge")
            lines.append(f"{k} {v}")
        for k, vals in sorted(self._histograms.items()):
            if vals:
                lines.append(f"# TYPE {k} summary")
                lines.append(f"{k}_count {len(vals)}")
                lines.append(f"{k}_sum {sum(vals)}")
        return "\n".join(lines) + "\n"
