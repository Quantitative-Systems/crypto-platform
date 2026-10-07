"""Crypto Trading Platform — Multi-Tenant Account & Trading Account Manager.

Enforces tenant data isolation and links encrypted exchange credentials.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import uuid

from crypto_platform.core.domain import OperatingMode, Tenant, TradingAccount
from crypto_platform.security.vault import SecurityVault


class AccountManager:
    """Manages multi-tenant accounts, exchange credentials, and operating modes."""

    def __init__(self, vault: Optional[SecurityVault] = None):
        self.vault = vault or SecurityVault()
        self.tenants: Dict[str, Tenant] = {}
        # account_id -> TradingAccount
        self.accounts: Dict[str, TradingAccount] = {}
        # account_id -> encrypted_secret
        self._encrypted_credentials: Dict[str, str] = {}

    def create_tenant(self, name: str) -> Tenant:
        tenant_id = f"t_{uuid.uuid4().hex[:8]}"
        tenant = Tenant(tenant_id=tenant_id, name=name)
        self.tenants[tenant_id] = tenant
        return tenant

    def create_trading_account(
        self,
        tenant_id: str,
        venue: str,
        api_key: str,
        api_secret: str,
        mode: OperatingMode = OperatingMode.PAPER,
    ) -> TradingAccount:
        if tenant_id not in self.tenants:
            raise KeyError(f"Tenant {tenant_id} does not exist")

        account_id = f"acc_{uuid.uuid4().hex[:8]}"
        account = TradingAccount(
            account_id=account_id,
            tenant_id=tenant_id,
            venue=venue,
            environment=mode,
            is_active=True,
        )

        # Store encrypted secret
        payload = f"{api_key}:{api_secret}"
        encrypted = self.vault.encrypt_secret(payload, tenant_id)
        self._encrypted_credentials[account_id] = encrypted

        self.accounts[account_id] = account
        return account

    def get_credentials(self, account_id: str, tenant_id: str) -> tuple[str, str]:
        """Decrypts and returns (api_key, api_secret) for execution worker."""
        encrypted = self._encrypted_credentials.get(account_id)
        if not encrypted:
            raise KeyError(f"No credentials found for account {account_id}")

        decrypted = self.vault.decrypt_secret(encrypted, tenant_id)
        api_key, api_secret = decrypted.split(":", 1)
        return api_key, api_secret

    def get_tenant_accounts(self, tenant_id: str) -> List[TradingAccount]:
        return [acc for acc in self.accounts.values() if acc.tenant_id == tenant_id]
