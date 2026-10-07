"""
Quantitative Crypto Platform (QCP) — Multi-Tenancy Engine.

Enforces strict tenant isolation across:
- User
- Organization
- Portfolio
- Account
- Exchange Connection
- Strategy Allocation
- Risk Policy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import uuid

from platform_core.foundation.error_taxonomy import TenantIsolationError


@dataclass
class Account:
    account_id: str
    portfolio_id: str
    name: str
    currency: str = "USDT"
    allocated_equity_usd: float = 0.0
    exchange_connections: List[str] = field(default_factory=list)


@dataclass
class Portfolio:
    portfolio_id: str
    org_id: str
    name: str
    accounts: Dict[str, Account] = field(default_factory=dict)
    active_strategies: Set[str] = field(default_factory=set)
    risk_policy_id: Optional[str] = None
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Organization:
    org_id: str
    name: str
    tier: str = "ENTERPRISE"
    portfolios: Dict[str, Portfolio] = field(default_factory=dict)
    users: Set[str] = field(default_factory=set)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def tenant_id(self) -> str:
        return self.org_id


@dataclass
class User:
    user_id: str
    org_id: str
    email: str
    role: str = "TRADER"  # ADMIN, TRADER, RISK_OFFICER, AUDITOR, READONLY
    mfa_enabled: bool = True


class TenantManager:
    """
    Central coordinator managing isolated multi-tenant contexts.
    """

    def __init__(self):
        self._orgs: Dict[str, Organization] = {}
        self._users: Dict[str, User] = {}
        self._create_default_tenant()

    def _create_default_tenant(self) -> None:
        org_id = "org_default"
        org = Organization(org_id=org_id, name="Quantitative Systems Global")
        port = Portfolio(portfolio_id="port_alpha", org_id=org_id, name="Alpha Core Portfolio", risk_policy_id="risk_policy_canonical")
        acc = Account(account_id="acc_main", portfolio_id="port_alpha", name="Main Trading Account", allocated_equity_usd=100_000.0)
        port.accounts[acc.account_id] = acc
        org.portfolios[port.portfolio_id] = port
        
        user = User(user_id="user_chief_quant", org_id=org_id, email="quant@quant-platform.internal", role="ADMIN")
        org.users.add(user.user_id)
        
        self._orgs[org_id] = org
        self._users[user.user_id] = user

    def create_organization(self, name: str, tier: str = "ENTERPRISE") -> Organization:
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        org = Organization(org_id=org_id, name=name, tier=tier)
        self._orgs[org_id] = org
        return org

    def assert_tenant_access(self, user_id: str, target_org_id: str) -> None:
        user = self._users.get(user_id)
        if not user:
            raise TenantIsolationError(f"User '{user_id}' does not exist.")
        if user.org_id != target_org_id:
            raise TenantIsolationError(
                f"TENANT ISOLATION BREACH: User '{user_id}' belonging to org '{user.org_id}' "
                f"attempted to access org '{target_org_id}'."
            )

    def get_organization(self, org_id: str) -> Optional[Organization]:
        return self._orgs.get(org_id)

    def get_portfolio(self, org_id: str, portfolio_id: str) -> Optional[Portfolio]:
        org = self._orgs.get(org_id)
        if not org:
            return None
        return org.portfolios.get(portfolio_id)

    # Convenience aliases for multi-tenancy contracts
    create_tenant = create_organization

    def create_account(self, tenant_id: str, name: str, initial_capital_usd: float = 100_000.0) -> Dict[str, Any]:
        org = self._orgs.get(tenant_id)
        if not org:
            raise TenantIsolationError(f"Tenant '{tenant_id}' not found.")
        acc_id = f"acc_{uuid.uuid4().hex[:8]}"
        # Store under default portfolio
        port_id = next(iter(org.portfolios.keys())) if org.portfolios else "default"
        if port_id not in org.portfolios:
            org.portfolios[port_id] = Portfolio(portfolio_id=port_id, org_id=tenant_id, name="Default")
        acc = Account(account_id=acc_id, portfolio_id=port_id, name=name, allocated_equity_usd=initial_capital_usd)
        org.portfolios[port_id].accounts[acc_id] = acc
        return {"account_id": acc_id, "name": name, "equity_usd": initial_capital_usd}

    def list_accounts(self, tenant_id: str) -> List[Dict[str, Any]]:
        org = self._orgs.get(tenant_id)
        if not org:
            return []
        accs = []
        for port in org.portfolios.values():
            for acc in port.accounts.values():
                accs.append({"account_id": acc.account_id, "name": acc.name, "equity_usd": acc.allocated_equity_usd})
        return accs

