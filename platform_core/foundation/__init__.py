"""
Quantitative Crypto Platform (QCP) — Platform Foundation Layer.
"""

from platform_core.foundation.config import PlatformConfig, get_platform_config
from platform_core.foundation.secrets_manager import SecretsManager
from platform_core.foundation.correlation import generate_event_id, CorrelationContext
from platform_core.foundation.clock import PlatformClock
from platform_core.foundation.audit_logger import AuditLogger
from platform_core.foundation.error_taxonomy import (
    QCPError,
    ConfigurationError,
    MarketDataError,
    RiskVetoError,
    ExecutionError,
    SecurityViolationError,
)
from platform_core.foundation.feature_flags import FeatureFlags
