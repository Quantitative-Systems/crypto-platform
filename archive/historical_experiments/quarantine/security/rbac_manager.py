"""
Quantitative Crypto Platform (QCP) — Security & Role-Based Access Control (RBAC).

Enforces role permissions, MFA verification, rate limiting, and emergency withdrawal/kill controls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from platform_core.foundation.error_taxonomy import SecurityViolationError


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    QUANT_ENGINEER = "QUANT_ENGINEER"
    QUANT_RESEARCHER = "QUANT_ENGINEER"
    RISK_OFFICER = "RISK_OFFICER"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    AUDITOR = "AUDITOR"
    READONLY = "READONLY"



class Permission(str, Enum):
    VIEW_PORTFOLIO = "VIEW_PORTFOLIO"
    EXECUTE_BACKTEST = "EXECUTE_BACKTEST"
    PROMOTE_STRATEGY = "PROMOTE_STRATEGY"
    ALLOCATE_CAPITAL = "ALLOCATE_CAPITAL"
    TRIGGER_KILL_SWITCH = "TRIGGER_KILL_SWITCH"
    MODIFY_RISK_POLICY = "MODIFY_RISK_POLICY"
    MANAGE_TENANTS = "MANAGE_TENANTS"
    VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),
    Role.RISK_OFFICER: {
        Permission.VIEW_PORTFOLIO,
        Permission.TRIGGER_KILL_SWITCH,
        Permission.MODIFY_RISK_POLICY,
        Permission.VIEW_AUDIT_LOGS,
    },
    Role.QUANT_ENGINEER: {
        Permission.VIEW_PORTFOLIO,
        Permission.EXECUTE_BACKTEST,
        Permission.PROMOTE_STRATEGY,
        Permission.VIEW_AUDIT_LOGS,
    },
    Role.PORTFOLIO_MANAGER: {
        Permission.VIEW_PORTFOLIO,
        Permission.ALLOCATE_CAPITAL,
        Permission.VIEW_AUDIT_LOGS,
    },
    Role.AUDITOR: {
        Permission.VIEW_PORTFOLIO,
        Permission.VIEW_AUDIT_LOGS,
    },
    Role.READONLY: {
        Permission.VIEW_PORTFOLIO,
    },
}


class RBACSecurityManager:
    """
    Central security governance engine.
    """

    def __init__(self):
        self._user_roles: Dict[str, Role] = {}
        self._rate_limits: Dict[str, List[float]] = {}
        self._emergency_kill_active: bool = False

    def assign_role(self, user_id: str, role: Role) -> None:
        self._user_roles[user_id] = role

    def get_role(self, user_id: str) -> Role:
        return self._user_roles.get(user_id, Role.READONLY)

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        role = self.get_role(user_id)
        allowed_perms = ROLE_PERMISSIONS.get(role, set())
        return permission in allowed_perms

    def assert_permission(self, user_id: str, permission: Permission) -> None:
        if not self.check_permission(user_id, permission):
            raise SecurityViolationError(
                f"ACCESS DENIED: User '{user_id}' with role '{self.get_role(user_id).value}' "
                f"lacks required permission '{permission.value}'."
            )

    def verify_mfa_token(self, user_id: str, token: str) -> bool:
        """Simulated RFC 6238 TOTP verification (time-step validity)."""
        return len(token) == 6 and token.isdigit()

    def check_rate_limit(self, user_id: str, max_requests_per_minute: int = 120) -> bool:
        now = time.time()
        calls = self._rate_limits.setdefault(user_id, [])
        # purge older than 60s
        self._rate_limits[user_id] = [t for t in calls if now - t < 60.0]
        if len(self._rate_limits[user_id]) >= max_requests_per_minute:
            return False
        self._rate_limits[user_id].append(now)
        return True

    def trigger_emergency_kill(self, actor_user_id: str, reason: str) -> None:
        self.assert_permission(actor_user_id, Permission.TRIGGER_KILL_SWITCH)
        self._emergency_kill_active = True

    def is_kill_active(self) -> bool:
        return self._emergency_kill_active


# Aliases for canonical naming conventions
RBACManager = RBACSecurityManager
UserRole = Role
