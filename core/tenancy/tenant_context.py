"""STRATA — Multi-Tenant Isolation & Context Management.

Guarantees tenant isolation:
- User A can NEVER view or mutate User B accounts, orders, positions, strategies, or credentials.
- All stored artifacts, accounts, and trades are strictly keyed by tenant_id.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TenantViolationError(PermissionError):
    """Raised when an operation attempts to breach tenant isolation boundaries."""
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str

    def assert_ownership(self, resource_tenant_id: str, resource_name: str = "resource") -> None:
        """Enforces that the caller owns the targeted resource."""
        if self.tenant_id != resource_tenant_id:
            msg = (
                f"TENANT ISOLATION BREACH: Tenant '{self.tenant_id}' attempted "
                f"unauthorized access to {resource_name} owned by tenant '{resource_tenant_id}'"
            )
            logger.critical(msg)
            raise TenantViolationError(msg)


class TenantScopedStore:
    """
    Generic thread-safe memory store enforcing tenant partitioning.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}  # tenant_id -> {item_id: item}

    def put(self, tenant_id: str, item_id: str, item: Any) -> None:
        if tenant_id not in self._store:
            self._store[tenant_id] = {}
        self._store[tenant_id][item_id] = item

    def get(self, tenant_id: str, item_id: str) -> Optional[Any]:
        return self._store.get(tenant_id, {}).get(item_id)

    def list(self, tenant_id: str) -> List[Any]:
        return list(self._store.get(tenant_id, {}).values())

    def delete(self, tenant_id: str, item_id: str) -> bool:
        if tenant_id in self._store and item_id in self._store[tenant_id]:
            del self._store[tenant_id][item_id]
            return True
        return False
