"""Unit tests for STRATA Security Hardening & Least-Privilege Controls."""
import pytest
from execution.safety.security_audit import (
    LeastPrivilegeGuard,
    SecurityScanner,
    SecurityViolationError,
)
from web.security_middleware import RateLimiter


def test_least_privilege_rejects_withdrawal_keys():
    # Key with withdrawal permissions enabled must fail
    malicious_perms = {
        "enableReading": True,
        "enableSpotAndMarginTrading": True,
        "enableWithdrawals": True,  # FORBIDDEN!
    }
    audit = LeastPrivilegeGuard.audit_permissions(malicious_perms)
    assert not audit.is_safe
    assert audit.can_withdraw
    assert "withdrawal" in audit.rejection_reason.lower()


def test_least_privilege_accepts_trade_only_keys():
    safe_perms = {
        "enableReading": True,
        "enableFutures": True,
        "enableWithdrawals": False,
    }
    audit = LeastPrivilegeGuard.audit_permissions(safe_perms)
    assert audit.is_safe
    assert audit.can_trade
    assert not audit.can_withdraw
    assert audit.rejection_reason is None


def test_security_scanner_detects_secrets():
    leak_text = "Here is my secret: 'abcdef12345678901234' on the server."
    findings = SecurityScanner.scan_content(leak_text)
    assert len(findings) > 0

    with pytest.raises(SecurityViolationError):
        SecurityScanner.assert_no_secrets(leak_text)


def test_rate_limiter_sliding_window():
    limiter = RateLimiter(max_requests_per_window=3, window_seconds=10.0)
    test_ip = "192.168.1.100"

    assert limiter.is_allowed(test_ip)
    assert limiter.is_allowed(test_ip)
    assert limiter.is_allowed(test_ip)
    # 4th request must be throttled
    assert not limiter.is_allowed(test_ip)
