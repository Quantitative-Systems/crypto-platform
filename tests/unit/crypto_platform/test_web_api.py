"""Unit tests for the Institutional REST & WebSocket API Gateway."""
import json
import pytest
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from crypto_platform.account_management.manager import AccountManager
from crypto_platform.api.server import PlatformWebServer, create_app
from crypto_platform.config.settings import PlatformSettings
from crypto_platform.security.vault import SecurityVault


class TestPlatformWebAPI(AioHTTPTestCase):
    async def get_application(self):
        settings = PlatformSettings(environment="PAPER", live_capital_usd=0.0)
        vault = SecurityVault()
        manager = AccountManager(vault=vault)
        self.server = PlatformWebServer(settings=settings, account_manager=manager, vault=vault)
        return create_app(self.server)

    async def test_index_page_serves_html(self):
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        text = await resp.text()
        assert "QUANTITATIVE PLATFORM" in text

    async def test_api_status(self):
        resp = await self.client.request("GET", "/api/status")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "HEALTHY"
        assert data["live_trading_locked"] is True
        assert data["live_capital_usd"] == 0.0

    async def test_api_get_accounts(self):
        resp = await self.client.request("GET", "/api/accounts")
        assert resp.status == 200
        data = await resp.json()
        assert "accounts" in data
        assert len(data["accounts"]) >= 1
        # Credentials must be masked with ellipsis or asterisks
        masked = data["accounts"][0]["api_key_masked"]
        assert "..." in masked or "***" in masked

    async def test_api_post_account_live_rejected(self):
        resp = await self.client.request("POST", "/api/accounts", json={
            "venue": "binance_futures",
            "api_key": "any_key",
            "api_secret": "any_secret",
            "mode": "LIVE",
        })
        assert resp.status == 403
        data = await resp.json()
        assert "strictly locked" in data["error"]

    async def test_api_post_account_demo_success(self):
        resp = await self.client.request("POST", "/api/accounts", json={
            "venue": "binance_futures_testnet",
            "api_key": "testnet_key_demo",
            "api_secret": "testnet_secret_demo",
            "mode": "DEMO",
        })
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "CONNECTED"
        assert "account_id" in data

    async def test_api_portfolio_and_positions(self):
        resp = await self.client.request("GET", "/api/portfolio")
        assert resp.status == 200
        data = await resp.json()
        assert data["current_equity_usd"] >= 100_000.0
        assert len(data["open_positions"]) > 0
        assert data["open_positions"][0]["symbol"] == "ADAUSDT"

    async def test_api_funnel_telemetry(self):
        resp = await self.client.request("GET", "/api/funnel")
        assert resp.status == 200
        data = await resp.json()
        assert "strategy_evaluations" in data
        assert "signals" in data

    async def test_api_strategies_and_toggle(self):
        resp = await self.client.request("GET", "/api/strategies")
        assert resp.status == 200
        data = await resp.json()
        assert len(data["strategies"]) == 10

        target_id = "promoted_intraday_trend_eth"
        toggle_resp = await self.client.request("POST", f"/api/strategies/{target_id}/toggle")
        assert toggle_resp.status == 200
        toggle_data = await toggle_resp.json()
        assert toggle_data["active"] is False

    async def test_api_emergency_kill(self):
        resp = await self.client.request("POST", "/api/emergency_kill")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "EMERGENCY_HALTED"

        # Verify status endpoint reflects emergency halt
        status_resp = await self.client.request("GET", "/api/status")
        status_data = await status_resp.json()
        assert status_data["status"] == "EMERGENCY_HALTED"
        assert status_data["emergency_kill_active"] is True
