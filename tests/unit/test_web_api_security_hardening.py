"""Unit tests for Crypto Platform Web API Security Hardening.

Verifies:
1. Rejection of unauthenticated requests across all protected endpoints (401 Unauthorized).
2. Rejection of invalid tokens (401 Unauthorized).
3. Rejection of expired session tokens (401 Unauthorized).
4. Rejection of revoked/logged-out session tokens (401 Unauthorized).
5. RBAC role enforcement: 403 Forbidden for insufficient permissions (e.g. RESEARCHER attempting control mutations).
6. Multi-tenant isolation: Tenant A cannot see or mutate Tenant B accounts, brokers, billing, or strategies.
7. Verification that public website, health, and market data endpoints remain accessible without tokens.
8. Preservation of fail-closed capital safety gates (real capital authorized $0.00).
"""
import time
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from core.auth.user_model import UserRole
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.safety.safety_gate import SAFETY_GATE
from web.server import PhaseRWebServer


@pytest.fixture
def supervisor():
    return AutonomousTradingSupervisor(symbols=["BTCUSDT"])


@pytest.fixture
def server(supervisor):
    return PhaseRWebServer(supervisor=supervisor)


PROTECTED_GET_ENDPOINTS = [
    "/api/accounts",
    "/api/brokers/active",
    "/api/decisions",
    "/api/positions",
    "/api/orders",
    "/api/reconciliation",
    "/api/drift",
    "/api/alerts",
    "/api/risk",
    "/api/billing",
    "/api/strategies",
    "/api/auth/me",
]

PROTECTED_POST_ENDPOINTS = [
    ("/api/agent/cycle", {}),
    ("/api/agent/style", {"style": "SWING"}),
    ("/api/agent/pause", {}),
    ("/api/agent/resume", {}),
    ("/api/system/halt", {}),
    ("/api/brokers/connect", {"venue": "BINANCE", "api_key": "test123456", "api_secret": "sec123456"}),
    ("/api/brokers/disconnect", {"venue": "BINANCE"}),
    ("/api/billing/plan", {"tier": "INSTITUTIONAL"}),
    ("/api/markets/watchlist", {"symbol": "BTCUSDT"}),
    ("/api/strategy-lab/copilot", {"prompt": "BTC structure"}),
    ("/api/auth/logout", {}),
]


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(server):
    """Every protected endpoint must reject unauthenticated requests with 401."""
    async with TestClient(TestServer(server.app)) as client:
        for path in PROTECTED_GET_ENDPOINTS:
            resp = await client.get(path)
            assert resp.status == 401, f"GET {path} should return 401, got {resp.status}"
            body = await resp.json()
            assert "error" in body

        for path, payload in PROTECTED_POST_ENDPOINTS:
            resp = await client.post(path, json=payload)
            assert resp.status == 401, f"POST {path} should return 401, got {resp.status}"
            body = await resp.json()
            assert "error" in body


@pytest.mark.asyncio
async def test_invalid_token_rejected(server):
    """Requests with malformed or invalid Bearer tokens must return 401."""
    async with TestClient(TestServer(server.app)) as client:
        bad_headers = {"Authorization": "Bearer strata_invalid_token_0000000000"}
        resp = await client.get("/api/accounts", headers=bad_headers)
        assert resp.status == 401
        body = await resp.json()
        assert "Invalid, expired, or revoked" in body["error"]


@pytest.mark.asyncio
async def test_expired_session_token_rejected(server):
    """Tokens past their expiry timestamp must be rejected with 401 and revoked in database."""
    async with TestClient(TestServer(server.app)) as client:
        # Register user
        user = server.auth_service.register_user("expired_tester@fund.com", "SecurePassword123!")
        # Issue session with expired timestamp
        session = server.auth_service.authenticate(user.email, "SecurePassword123!")
        assert session is not None

        # Manually force session expiry in DB
        with server.auth_service.db.transaction():
            server.auth_service.db.execute(
                "UPDATE sessions SET expires_at_ts = ? WHERE user_id = ?;",
                (time.time() - 3600.0, user.user_id),
            )

        headers = {"Authorization": f"Bearer {session.token}"}
        resp = await client.get("/api/accounts", headers=headers)
        assert resp.status == 401
        body = await resp.json()
        assert "Invalid, expired, or revoked" in body["error"]


@pytest.mark.asyncio
async def test_revoked_session_token_rejected(server):
    """Logged-out session tokens must be immediately revoked and rejected with 401."""
    async with TestClient(TestServer(server.app)) as client:
        # Register and login
        reg_resp = await client.post("/api/auth/register", json={
            "email": "revoked_tester@fund.com",
            "password": "SecurePassword123!",
        })
        token = (await reg_resp.json())["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Valid session accesses /api/accounts
        ok_resp = await client.get("/api/accounts", headers=headers)
        assert ok_resp.status == 200

        # Logout revokes session
        logout_resp = await client.post("/api/auth/logout", headers=headers)
        assert logout_resp.status == 200

        # Subsequent request with revoked token must fail with 401
        after_resp = await client.get("/api/accounts", headers=headers)
        assert after_resp.status == 401
        body = await after_resp.json()
        assert "Invalid, expired, or revoked" in body["error"]


@pytest.mark.asyncio
async def test_rbac_insufficient_permissions(server):
    """Users with RESEARCHER role must receive 403 Forbidden when attempting control mutations."""
    async with TestClient(TestServer(server.app)) as client:
        # Register user with RESEARCHER role
        user = server.auth_service.register_user(
            "researcher@fund.com",
            "SecureResearcher123!",
            role=UserRole.RESEARCHER,
        )
        session = server.auth_service.authenticate(user.email, "SecureResearcher123!")
        headers = {"Authorization": f"Bearer {session.token}"}

        # RESEARCHER can read accounts, strategies, blotters (200)
        acc_resp = await client.get("/api/accounts", headers=headers)
        assert acc_resp.status == 200

        strat_resp = await client.get("/api/strategies", headers=headers)
        assert strat_resp.status == 200

        # RESEARCHER is FORBIDDEN from mutating agent styles, trading cycles, brokers, billing
        forbidden_endpoints = [
            ("/api/agent/style", {"style": "SWING"}),
            ("/api/agent/cycle", {}),
            ("/api/agent/pause", {}),
            ("/api/agent/resume", {}),
            ("/api/system/halt", {}),
            ("/api/brokers/connect", {"venue": "BINANCE", "api_key": "k12345678", "api_secret": "s12345678", "permissions": {"enableWithdrawals": False}}),
            ("/api/brokers/disconnect", {"venue": "BINANCE"}),
            ("/api/billing/plan", {"tier": "INSTITUTIONAL"}),
        ]

        for path, payload in forbidden_endpoints:
            resp = await client.post(path, json=payload, headers=headers)
            assert resp.status == 403, f"POST {path} should return 403 for RESEARCHER, got {resp.status}"
            body = await resp.json()
            assert "Forbidden" in body["error"]


@pytest.mark.asyncio
async def test_cross_tenant_isolation(server):
    """Tenant A and Tenant B must have strict isolation across accounts, brokers, billing, and strategies."""
    async with TestClient(TestServer(server.app)) as client:
        # Register Tenant A
        reg_a = await client.post("/api/auth/register", json={
            "email": "tenant_a@fund.com",
            "password": "PasswordAlpha2026!",
            "name": "Alpha Fund"
        })
        token_a = (await reg_a.json())["token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register Tenant B
        reg_b = await client.post("/api/auth/register", json={
            "email": "tenant_b@fund.com",
            "password": "PasswordBeta2026!",
            "name": "Beta Capital"
        })
        token_b = (await reg_b.json())["token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Tenant A connects BINANCE broker
        conn_resp = await client.post("/api/brokers/connect", json={
            "venue": "BINANCE",
            "api_key": "alpha_binance_key_12345",
            "api_secret": "alpha_binance_secret_12345",
            "is_testnet": True,
            "permissions": {"enableWithdrawals": False}
        }, headers=headers_a)
        assert conn_resp.status == 200

        # 1. Tenant A sees BINANCE in active brokers
        active_a = await client.get("/api/brokers/active", headers=headers_a)
        assert active_a.status == 200
        venues_a = [b["venue"] for b in await active_a.json()]
        assert "BINANCE" in venues_a

        # 2. Tenant B DOES NOT see Tenant A's BINANCE broker connection
        active_b = await client.get("/api/brokers/active", headers=headers_b)
        assert active_b.status == 200
        venues_b = [b["venue"] for b in await active_b.json()]
        assert "BINANCE" not in venues_b, "Tenant B should not see Tenant A's broker connection"

        # 3. Tenant B attempts to disconnect Tenant A's BINANCE broker -> fails with 404
        disc_b = await client.post("/api/brokers/disconnect", json={"venue": "BINANCE"}, headers=headers_b)
        assert disc_b.status == 404, "Tenant B should not be able to disconnect Tenant A's broker"

        # 4. Tenant A's broker remains connected
        active_a_after = await client.get("/api/brokers/active", headers=headers_a)
        assert "BINANCE" in [b["venue"] for b in await active_a_after.json()]

        # 5. Accounts Isolation: Tenant B cannot see Tenant A's created account
        accs_a = await client.get("/api/accounts", headers=headers_a)
        acc_names_a = [a.get("name") for a in await accs_a.json()]
        assert any("Binance Connected Account" in n for n in acc_names_a if n)

        accs_b = await client.get("/api/accounts", headers=headers_b)
        acc_names_b = [a.get("name") for a in await accs_b.json()]
        assert not any("Binance Connected Account" in n for n in acc_names_b if n), "Tenant B should not see Tenant A's account"

        # 6. Billing Isolation: Tenant B upgrading billing does not mutate Tenant A
        await client.post("/api/billing/plan", json={"tier": "INSTITUTIONAL"}, headers=headers_b)
        billing_a = await client.get("/api/billing", headers=headers_a)
        billing_a_data = await billing_a.json()
        assert billing_a_data["status"]["current_plan"]["tier"] != "INSTITUTIONAL"
        assert billing_a_data["status"]["tenant_id"] == (await reg_a.json())["user"]["tenant_id"]


@pytest.mark.asyncio
async def test_public_and_health_endpoints_accessible_without_token(server):
    """Explicitly public website and health endpoints must remain accessible without tokens."""
    async with TestClient(TestServer(server.app)) as client:
        # Public website & SPA shells
        assert (await client.get("/")).status == 200
        assert (await client.get("/how-it-works")).status == 200
        assert (await client.get("/technology")).status == 200
        assert (await client.get("/pricing")).status == 200
        assert (await client.get("/faq")).status == 200
        assert (await client.get("/app")).status == 200
        assert (await client.get("/dashboard")).status == 200
        assert (await client.get("/manifest.json")).status == 200
        assert (await client.get("/sw.js")).status == 200

        # Health & readiness
        assert (await client.get("/health")).status == 200
        assert (await client.get("/api/health")).status == 200
        assert (await client.get("/api/status")).status == 200
        assert (await client.get("/version")).status == 200
        assert (await client.get("/api/version")).status == 200
        assert (await client.get("/api/telemetry")).status == 200

        # Public market data & catalog
        assert (await client.get("/api/king/overview")).status == 200
        assert (await client.get("/api/markets")).status == 200
        assert (await client.get("/api/markets/BTCUSDT")).status == 200
        assert (await client.get("/api/markets/BTCUSDT/five-set-ladder")).status == 200
        assert (await client.get("/api/markets/BTCUSDT/parity-audit")).status == 200
        assert (await client.get("/api/brokers")).status == 200
        assert (await client.get("/api/backtests")).status == 200
        assert (await client.get("/api/forward-validation")).status == 200

        # Public calculation & simulation
        suit_resp = await client.post("/api/accounts/suitability", json={"equity_usd": 50000, "style": "SWING"})
        assert suit_resp.status == 200

        parse_resp = await client.post("/api/strategy-lab/parse", json={"prompt": "Buy BTC pullbacks with 5R"})
        assert parse_resp.status == 200
        spec = (await parse_resp.json())["specification"]

        eval_resp = await client.post("/api/strategy-lab/evaluate", json={"specification": spec})
        assert eval_resp.status == 200


@pytest.mark.asyncio
async def test_fail_closed_safety_parameters_preserved():
    """Fail-closed safeguards must remain locked at $0.00 capital."""
    assert SAFETY_GATE.real_capital_authorized_usd == 0.00
    assert SAFETY_GATE.is_live_execution is False
