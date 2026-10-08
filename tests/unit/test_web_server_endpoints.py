"""Unit tests for STRATA Web Server, Public Website, Terminal, and REST APIs."""
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from web.server import PhaseRWebServer


@pytest.fixture
def test_supervisor():
    return AutonomousTradingSupervisor(symbols=["BTCUSDT"])


@pytest.fixture
def test_server(test_supervisor):
    return PhaseRWebServer(supervisor=test_supervisor)


@pytest.mark.asyncio
async def test_public_website_and_terminal_html_routes(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Root engineering & admin page
        resp = await client.get("/")
        assert resp.status == 200
        html = await resp.text()
        assert "Crypto Platform" in html
        assert "Android" in html

        # 2. Terminal app page
        resp_app = await client.get("/app")
        assert resp_app.status == 200
        app_html = await resp_app.text()
        assert "Crypto Platform" in app_html

        # 3. Mobile application route
        resp_mobile = await client.get("/mobile")
        assert resp_mobile.status == 200
        mobile_html = await resp_mobile.text()
        assert "Crypto Platform" in mobile_html



@pytest.mark.asyncio
async def test_api_health_and_telemetry(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        resp = await client.get("/api/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["real_capital_authorized"] == 0.0
        assert data["live_trading_status"] == "DISABLED_FAIL_CLOSED"
        assert data["execution_mode"] == "PAPER"
        assert data["status"] in ("HEALTHY", "DEGRADED")


@pytest.mark.asyncio
async def test_api_auth_lifecycle(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # Register
        reg_resp = await client.post("/api/auth/register", json={
            "email": "quant@fund.com",
            "password": "StrongSecret2026!",
        })
        assert reg_resp.status == 200
        reg_data = await reg_resp.json()
        assert reg_data["user"]["email"] == "quant@fund.com"
        token = reg_data["token"]
        assert token is not None

        # Get /me
        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status == 200
        me_data = await me_resp.json()
        assert me_data["email"] == "quant@fund.com"

        # Logout
        logout_resp = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout_resp.status == 200


@pytest.mark.asyncio
async def test_api_strategy_lab_parse_and_evaluate(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        parse_resp = await client.post("/api/strategy-lab/parse", json={
            "prompt": "Buy BTC pullbacks when daily and 4h structure is bullish with 5R target",
        })
        assert parse_resp.status == 200
        parse_data = await parse_resp.json()
        spec = parse_data["specification"]
        assert "BTCUSDT" in spec["assets"]
        assert "5R" in spec["target_rule"]

        # Evaluate
        eval_resp = await client.post("/api/strategy-lab/evaluate", json={"specification": spec})
        assert eval_resp.status == 200
        eval_data = await eval_resp.json()
        assert eval_data["verdict"] in ("PAPER_ELIGIBLE", "FORWARD_VALIDATION_ELIGIBLE", "NOT_READY")
        assert "disclaimer" in eval_data


@pytest.mark.asyncio
async def test_api_brokers_and_agent_controls(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # List brokers
        brk_resp = await client.get("/api/brokers")
        assert brk_resp.status == 200
        brokers = await brk_resp.json()
        assert len(brokers) == 3

        # Agent style update
        style_resp = await client.post("/api/agent/style", json={"style": "SWING"})
        assert style_resp.status == 200
        assert (await style_resp.json())["style"] == "SWING"

        # Agent cycle
        cycle_resp = await client.post("/api/agent/cycle")
        assert cycle_resp.status == 200
        cycle_data = await cycle_resp.json()
        assert cycle_data["market_health"] == "HEALTHY"
