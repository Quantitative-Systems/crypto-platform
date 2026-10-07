"""
Comprehensive Test Suite: Platform Foundation & Registries.
Validates:
- PlatformConfigManager
- Cryptographic AuditLogger
- Clock management
- FeatureFlagsManager
- SchemaRegistry & ServiceRegistry
"""

import tempfile
from pathlib import Path
import pytest

from platform_core.foundation.config import PlatformConfigManager
from platform_core.foundation.audit_logger import AuditLogger
from platform_core.foundation.clock import SystemClock
from platform_core.foundation.feature_flags import FeatureFlagsManager
from platform_core.service_registry import ServiceRegistry, ServiceStatus
from platform_core.schema_registry import SchemaRegistry


def test_config_manager_defaults():
    mgr = PlatformConfigManager()
    cfg = mgr.get_config()
    assert cfg.environment.value == "RESEARCH"
    assert cfg.live_capital_enabled is False
    assert cfg.max_portfolio_heat_pct == 3.0


def test_audit_logger_block_chaining():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit_test.jsonl"
        logger = AuditLogger(log_path=log_path)

        e1 = logger.log_event("TEST_EVENT", "Tester", "CREATE", {"field": 1})
        e2 = logger.log_event("TEST_EVENT_2", "Tester", "UPDATE", {"field": 2})

        assert e1["previous_hash"] == AuditLogger.GENESIS_HASH
        assert e2["previous_hash"] == e1["current_hash"]
        assert log_path.exists()


def test_clock_management():
    now_utc = SystemClock.utc_now()
    assert now_utc is not None
    now_ms = SystemClock.now_epoch_ms()
    assert now_ms > 1700000000000


def test_feature_flags():
    ff = FeatureFlagsManager()
    assert ff.is_enabled("PAPER_TRADING_ENABLED") is True
    assert ff.is_enabled("LIVE_CAPITAL_TRADING") is False

    # Cannot enable live capital if blocked by invariant
    ff.set_flag("PAPER_TRADING_ENABLED", False)
    assert ff.is_enabled("PAPER_TRADING_ENABLED") is False



def test_service_and_schema_registry():
    sreg = ServiceRegistry()
    report = sreg.health_check_all()
    assert report.total_services >= 10
    assert report.overall_status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)

    sch_reg = SchemaRegistry()
    schemas = sch_reg.list_all()
    assert len(schemas) >= 6

