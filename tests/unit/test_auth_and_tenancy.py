"""Unit tests for STRATA Authentication and Multi-Tenant Isolation."""
import pytest
from core.auth.auth_service import AuthService
from core.auth.user_model import UserRole
from core.tenancy.tenant_context import TenantContext, TenantScopedStore, TenantViolationError


def test_auth_service_registration_and_authentication():
    service = AuthService()

    # Successful registration
    user = service.register_user("trader@strata.io", "StrataSecure2026!", role=UserRole.TRADER)
    assert user.email == "trader@strata.io"
    assert user.tenant_id.startswith("tenant_")
    assert user.is_active is True

    # Duplicate registration blocked
    with pytest.raises(ValueError, match="already exists"):
        service.register_user("trader@strata.io", "DifferentPassword123!")

    # Invalid email blocked
    with pytest.raises(ValueError, match="Invalid email"):
        service.register_user("not-an-email", "StrataSecure2026!")

    # Password too short
    with pytest.raises(ValueError, match="at least 8 characters"):
        service.register_user("user2@strata.io", "short")

    # Invalid login fails
    session = service.authenticate("trader@strata.io", "WrongPassword!")
    assert session is None

    # Valid login succeeds
    session = service.authenticate("trader@strata.io", "StrataSecure2026!")
    assert session is not None
    assert session.user_id == user.user_id
    assert session.tenant_id == user.tenant_id
    assert session.token.startswith("strata_")

    # Token validation
    authenticated_user = service.validate_session(session.token)
    assert authenticated_user is not None
    assert authenticated_user.email == "trader@strata.io"

    # Logout
    assert service.logout(session.token) is True
    assert service.validate_session(session.token) is None


def test_multi_tenant_isolation_enforcement():
    service = AuthService()
    user_a = service.register_user("alpha@strata.io", "AlphaPass2026!")
    user_b = service.register_user("beta@strata.io", "BetaPass2026!")

    ctx_a = TenantContext(tenant_id=user_a.tenant_id, user_id=user_a.user_id)
    ctx_b = TenantContext(tenant_id=user_b.tenant_id, user_id=user_b.user_id)

    # Store items for tenant A and tenant B
    store = TenantScopedStore()
    store.put(user_a.tenant_id, "acc_1", {"balance": 50000.0, "broker": "BINANCE"})
    store.put(user_b.tenant_id, "acc_2", {"balance": 100000.0, "broker": "BYBIT"})

    # Tenant A accesses own item
    ctx_a.assert_ownership(user_a.tenant_id, "account")
    assert store.get(user_a.tenant_id, "acc_1")["balance"] == 50000.0

    # Tenant A attempts to access Tenant B's resource -> strictly blocked!
    with pytest.raises(TenantViolationError, match="TENANT ISOLATION BREACH"):
        ctx_a.assert_ownership(user_b.tenant_id, "account")

    # Scoped store guarantees Tenant A cannot see Tenant B's items
    items_a = store.list(user_a.tenant_id)
    assert len(items_a) == 1
    assert items_a[0]["broker"] == "BINANCE"

    items_b = store.list(user_b.tenant_id)
    assert len(items_b) == 1
    assert items_b[0]["broker"] == "BYBIT"
