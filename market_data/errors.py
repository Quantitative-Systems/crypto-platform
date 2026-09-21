"""
Quantitative Crypto Platform (QCP) — Canonical Error Taxonomy.

Hierarchical exception taxonomy providing precise error classification,
fail-closed panics, and telemetry error codes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCategory(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    CAPITAL = "CAPITAL"
    MARKET_DATA = "MARKET_DATA"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    GOVERNANCE = "GOVERNANCE"
    SECURITY = "SECURITY"


class ErrorSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QCPError(Exception):
    """Root base exception for all QCP platform components."""

    error_code: str = "ERR_GENERIC_PLATFORM"

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.CONFIGURATION,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}


    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


PlatformError = QCPError


class ConfigurationError(QCPError):
    error_code = "ERR_CONFIGURATION_INVALID"


class CapitalFirewallError(QCPError):
    error_code = "ERR_CAPITAL_FIREWALL_VIOLATION"


class MarketDataError(QCPError):
    error_code = "ERR_MARKET_DATA_FAILURE"


class DataCorruptionError(MarketDataError):
    error_code = "ERR_DATA_CORRUPTION_DETECTED"


class RiskVetoError(QCPError):
    error_code = "ERR_RISK_FIREWALL_VETO"


class PortfolioHeatViolationError(RiskVetoError):
    error_code = "ERR_PORTFOLIO_HEAT_CEILING_EXCEEDED"


class ExecutionError(QCPError):
    error_code = "ERR_EXECUTION_FAILURE"


class SecurityViolationError(QCPError):
    error_code = "ERR_SECURITY_VIOLATION"


class TenantIsolationError(SecurityViolationError):
    error_code = "ERR_TENANT_ISOLATION_BREACH"
