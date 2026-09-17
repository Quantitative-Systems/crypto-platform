"""
Quantitative Crypto Platform (QCP) — Canonical Service Registry.

Authoritative runtime catalog managing service lifecycle, health statuses,
dependencies, and graceful startup/shutdown choreography.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ServiceStatus(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    HALTED = "HALTED"
    FAILED = "FAILED"


@dataclass
class ServiceDescriptor:
    service_id: str
    name: str
    description: str
    layer_index: int
    dependencies: List[str]
    status: ServiceStatus = ServiceStatus.UNINITIALIZED
    health_check_fn: Optional[Callable[[], bool]] = None
    last_health_check_utc: Optional[str] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "layer_index": self.layer_index,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "last_health_check_utc": self.last_health_check_utc,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }


@dataclass
class PlatformHealthReport:
    overall_status: ServiceStatus
    total_services: int
    healthy_services: int
    services: Dict[str, Any]
    timestamp_utc: str



class ServiceRegistry:
    """
    Singleton service coordinator tracking all running platform microservices and daemons.
    """

    _instance: Optional[ServiceRegistry] = None

    def __new__(cls) -> ServiceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._register_core_services()
        return cls._instance

    def _register_core_services(self) -> None:
        core = [
            ServiceDescriptor("foundation.config", "Configuration Engine", "Configuration & Environment", 0, []),
            ServiceDescriptor("foundation.audit", "Audit Logger", "Cryptographic Audit Ledger", 0, []),
            ServiceDescriptor("market_data.warehouse", "Market Data Warehouse", "Historical Kline & Series Loader", 1, []),
            ServiceDescriptor("market_data.realtime", "Realtime Stream Manager", "WebSocket Market Ingestion", 1, ["market_data.warehouse"]),
            ServiceDescriptor("research.evaluator", "Research Evaluation Engine", "Causal Backtest & Discovery Lab", 2, ["market_data.warehouse"]),
            ServiceDescriptor("strategy.factory", "Strategy Factory", "Modular Strategy Generator", 3, ["research.evaluator"]),
            ServiceDescriptor("portfolio.allocator", "Capital Allocator", "Generic Multi-Slot Allocator", 4, ["strategy.factory"]),
            ServiceDescriptor("risk.firewall", "Portfolio Risk Firewall", "7-D Portfolio Risk Firewall", 5, ["portfolio.allocator"]),
            ServiceDescriptor("execution.gateway", "Execution OS", "Paper Order Manager & Router", 6, ["risk.firewall"]),
            ServiceDescriptor("derivatives.pricer", "Derivatives & Options Engine", "Black-Scholes & Greeks Engine", 7, ["market_data.warehouse"]),
            ServiceDescriptor("market_making.engine", "Market Making Engine", "Avellaneda-Stoikov Paper Quoter", 7, ["execution.gateway"]),
            ServiceDescriptor("hft.event_bus", "Low Latency Event Bus", "Zero-Copy Pub/Sub Bus", 8, []),
            ServiceDescriptor("production.paper_daemon", "Forward Paper Daemon", "24/7 Forward Burn-In Observer", 9, ["execution.gateway", "risk.firewall"]),
            ServiceDescriptor("security.rbac", "Security & RBAC", "Authentication & Access Control", 10, []),
            ServiceDescriptor("multi_tenancy.manager", "Tenant Manager", "Multi-Tenant Isolation Manager", 10, ["security.rbac"]),
            ServiceDescriptor("billing.saas", "SaaS Billing Engine", "Subscription & Entitlement Engine", 10, ["multi_tenancy.manager"]),
            ServiceDescriptor("observability.telemetry", "Observability Exporter", "Prometheus Metrics & Health", 10, []),
            ServiceDescriptor("dr.chaos", "Disaster Recovery Orchestrator", "State Recovery & Fault Injection", 10, ["execution.gateway"]),
            ServiceDescriptor("web.app", "Institutional Web Console", "FastAPI & Modern Web Dashboard", 11, ["production.paper_daemon", "observability.telemetry"]),
        ]
        for s in core:
            self._services[s.service_id] = s

    def register(self, descriptor: ServiceDescriptor) -> None:
        self._services[descriptor.service_id] = descriptor

    def get(self, service_id: str) -> Optional[ServiceDescriptor]:
        return self._services.get(service_id)

    def set_status(self, service_id: str, status: ServiceStatus, error: Optional[str] = None) -> None:
        if service_id in self._services:
            self._services[service_id].status = status
            self._services[service_id].last_health_check_utc = datetime.now(timezone.utc).isoformat()
            self._services[service_id].last_error = error

    def check_all_health(self) -> Dict[str, Any]:
        results = {}
        for sid, s in self._services.items():
            if s.health_check_fn:
                try:
                    ok = s.health_check_fn()
                    s.status = ServiceStatus.HEALTHY if ok else ServiceStatus.DEGRADED
                except Exception as e:
                    s.status = ServiceStatus.FAILED
                    s.last_error = str(e)
            s.last_health_check_utc = datetime.now(timezone.utc).isoformat()
            results[sid] = s.to_dict()
        return results

    def list_services(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in sorted(self._services.values(), key=lambda x: x.layer_index)]

    def health_check_all(self) -> PlatformHealthReport:
        res = self.check_all_health()
        total = len(self._services)
        healthy = sum(1 for s in self._services.values() if s.status == ServiceStatus.HEALTHY)
        failed = sum(1 for s in self._services.values() if s.status == ServiceStatus.FAILED)
        overall = ServiceStatus.HEALTHY if failed == 0 else ServiceStatus.DEGRADED
        return PlatformHealthReport(
            overall_status=overall,
            total_services=total,
            healthy_services=healthy,
            services=res,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

