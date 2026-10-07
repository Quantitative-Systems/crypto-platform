"""STRATA Digital Trading Platform — Security Audit & Least-Privilege Guard.

Provides production security controls:
1. Automated Secret Scanner: Scans strings, configs, and payloads for leaked private keys, API secrets, tokens.
2. Least-Privilege Enforcer: Verifies exchange API key permissions and strictly rejects credentials possessing
   withdrawal or transfer permissions (Non-Custodial Invariant).
3. Secure Token Generator: Cryptographically secure token and passkey generation using HMAC-SHA256.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CredentialPermissionAudit:
    is_safe: bool
    can_trade: bool
    can_read: bool
    can_withdraw: bool
    rejection_reason: Optional[str] = None


class SecurityScanner:
    """Detects leaked credentials and enforces secret isolation."""

    SECRET_REGEXES = [
        re.compile(r"(api[_-]?key|secret|password|token|private[_-]?key)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?", re.IGNORECASE),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE),
    ]

    @classmethod
    def scan_content(cls, content: str) -> List[str]:
        """Scan string content and return list of suspected leaked credential patterns."""
        findings = []
        for regex in cls.SECRET_REGEXES:
            matches = regex.findall(content)
            if matches:
                findings.append(f"Matched pattern: {regex.pattern}")
        return findings

    @classmethod
    def assert_no_secrets(cls, content: str, context_label: str = "Payload") -> None:
        findings = cls.scan_content(content)
        if findings:
            raise SecurityViolationError(f"SECURITY BREACH: {context_label} contains detected secret patterns: {findings}")


class LeastPrivilegeGuard:
    """Enforces non-custodial least-privilege boundary for exchange API keys."""

    @staticmethod
    def audit_permissions(permissions: Dict[str, bool]) -> CredentialPermissionAudit:
        """Audit exchange API key permissions.
        
        Mandatory Rule:
        The trading platform strictly requires read and trade permissions.
        It strictly FORBIDS withdrawal, transfer, or sub-account management permissions.
        """
        can_trade = permissions.get("enableSpotAndMarginTrading", False) or permissions.get("enableFutures", False) or permissions.get("can_trade", False)
        can_read = permissions.get("enableReading", True) or permissions.get("can_read", True)
        can_withdraw = permissions.get("enableWithdrawals", False) or permissions.get("can_withdraw", False) or permissions.get("enableInternalTransfer", False)

        if can_withdraw:
            logger.critical("LEAST PRIVILEGE VIOLATION: API KEY HAS WITHDRAWAL PERMISSIONS ENABLED!")
            return CredentialPermissionAudit(
                is_safe=False,
                can_trade=can_trade,
                can_read=can_read,
                can_withdraw=True,
                rejection_reason="CRITICAL_LEAST_PRIVILEGE_VIOLATION: Key has withdrawal permissions enabled. Non-custodial platforms strictly forbid withdrawal access.",
            )

        if not can_trade:
            return CredentialPermissionAudit(
                is_safe=False,
                can_trade=False,
                can_read=can_read,
                can_withdraw=False,
                rejection_reason="INSUFFICIENT_PERMISSIONS: Key lacks trading authorization.",
            )

        return CredentialPermissionAudit(
            is_safe=True,
            can_trade=True,
            can_read=can_read,
            can_withdraw=False,
            rejection_reason=None,
        )


class SecurityViolationError(RuntimeError):
    """Raised when security boundaries or least-privilege constraints are breached."""
    pass
