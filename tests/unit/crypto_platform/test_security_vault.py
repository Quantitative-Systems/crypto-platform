"""Tests for Security Vault and Multi-Tenant Account Management."""
import pytest
from crypto_platform.account_management.manager import AccountManager
from crypto_platform.core.domain import OperatingMode
from crypto_platform.security.vault import SecurityVault


def test_security_vault_encryption_roundtrip():
    vault = SecurityVault()
    secret = "binance_super_secret_api_key_12345"
    tenant_id = "tenant_alpha"

    ciphertext = vault.encrypt_secret(secret, tenant_id)
    assert ciphertext != secret
    assert len(ciphertext) > 32

    decrypted = vault.decrypt_secret(ciphertext, tenant_id)
    assert decrypted == secret


def test_security_vault_cross_tenant_isolation():
    vault = SecurityVault()
    secret = "secret_for_tenant_1"

    ciphertext = vault.encrypt_secret(secret, "tenant_1")

    # Attempting to decrypt with tenant_2 key must fail authentication
    with pytest.raises(Exception):
        vault.decrypt_secret(ciphertext, "tenant_2")


def test_security_vault_tampered_ciphertext():
    vault = SecurityVault()
    secret = "test_secret"
    ciphertext = vault.encrypt_secret(secret, "t1")

    # Corrupt last character of base64
    corrupted = ciphertext[:-2] + ("A" if ciphertext[-2] != "A" else "B") + "="
    with pytest.raises(Exception):
        vault.decrypt_secret(corrupted, "t1")


def test_api_key_masking():
    vault = SecurityVault()
    masked = vault.mask_api_key("apiKey1234567890abcdef")
    assert masked.startswith("apiK...")
    assert masked.endswith("cdef")


def test_account_manager_multi_tenant_flow():
    mgr = AccountManager()
    t1 = mgr.create_tenant("Fund 1")
    t2 = mgr.create_tenant("Fund 2")

    acc1 = mgr.create_trading_account(
        tenant_id=t1.tenant_id,
        venue="binance",
        api_key="k1",
        api_secret="s1",
        mode=OperatingMode.PAPER,
    )
    assert acc1.tenant_id == t1.tenant_id
    assert acc1.is_active is True

    # Decrypt credentials for t1
    k, s = mgr.get_credentials(acc1.account_id, t1.tenant_id)
    assert k == "k1"
    assert s == "s1"

    # Cross-tenant access must fail
    with pytest.raises(Exception):
        mgr.get_credentials(acc1.account_id, t2.tenant_id)

    # List tenant accounts
    t1_accounts = mgr.get_tenant_accounts(t1.tenant_id)
    assert len(t1_accounts) == 1
    assert t1_accounts[0].account_id == acc1.account_id

    t2_accounts = mgr.get_tenant_accounts(t2.tenant_id)
    assert len(t2_accounts) == 0
