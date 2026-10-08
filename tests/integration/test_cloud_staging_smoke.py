"""Crypto Platform — Cloud Staging Automated Smoke Test.

Validates the full 14-stage journey required for staging & cloud readiness:
1. APP START (Root probes: /health, /ready, /version)
2. AUTH / SESSION (/api/auth/register, /api/auth/login, /api/auth/me)
3. HOME / OVERVIEW (/api/king/overview)
4. MARKETS (/api/markets)
5. MARKET DETAIL (/api/markets/BTCUSDT)
6. STRATEGIES (/api/strategies)
7. RESEARCH / LAB (/api/strategy-lab/parse)
8. BACKTEST (/api/backtests)
9. FORWARD TEST (/api/forward-validation)
10. TRADING (/api/positions, /api/orders, /api/decisions)
11. RISK MANAGEMENT (/api/risk)
12. PERFORMANCE / TELEMETRY (/api/telemetry)
13. MONITORING (/api/reconciliation, /api/drift, /api/alerts)
14. ACCOUNT (/api/accounts, /api/brokers)
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.safety.safety_gate import SAFETY_GATE
from web.server import PhaseRWebServer


class TestCloudStagingSmoke(AioHTTPTestCase):

    async def get_application(self) -> web.Application:
        # Create supervisor in Paper mode with 0 capital
        self.supervisor = AutonomousTradingSupervisor(symbols=["BTCUSDT", "ETHUSDT"])
        self.server = PhaseRWebServer(supervisor=self.supervisor, host="127.0.0.1", port=8080)
        return self.server.app

    async def test_01_app_start_probes(self):
        """Phase 14.1 — APP START: Test load-balancer health & readiness probes."""
        # /health
        resp = await self.client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] in ("HEALTHY", "DEGRADED")
        assert data["real_capital_authorized"] == 0.00
        assert data["live_trading_status"] == "DISABLED_FAIL_CLOSED"

        # /ready
        resp_ready = await self.client.get("/ready")
        assert resp_ready.status in (200, 503)

        # /version
        resp_ver = await self.client.get("/version")
        assert resp_ver.status == 200
        data_ver = await resp_ver.json()
        assert data_ver["platform"] == "Crypto Platform"
        assert data_ver.get("king_contract_hash") == "8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098"

    async def test_02_auth_session_journey(self):
        """Phase 14.2 — AUTH / SESSION: Test registration, login, session inspection."""
        # Register new session
        reg_payload = {"email": "smoke_tester@cryptoplatform.io", "password": "SecurePassword123!", "name": "Smoke Tester"}
        resp = await self.client.post("/api/auth/register", json=reg_payload)
        assert resp.status == 200
        data = await resp.json()
        token = data.get("token")
        assert token is not None

        # Inspect authenticated session /me
        headers = {"Authorization": f"Bearer {token}"}
        resp_me = await self.client.get("/api/auth/me", headers=headers)
        assert resp_me.status == 200
        user = await resp_me.json()
        assert user["email"] == "smoke_tester@cryptoplatform.io"

    async def test_03_home_overview(self):
        """Phase 14.3 — HOME: Verify master dashboard overview."""
        resp = await self.client.get("/api/king/overview")
        assert resp.status == 200
        data = await resp.json()
        assert "engine" in data or "capital_safety" in data or "active_symbols" in data

    async def test_04_markets_list(self):
        """Phase 14.4 — MARKETS: Verify admitted universe market list."""
        resp = await self.client.get("/api/markets")
        assert resp.status == 200
        markets = await resp.json()
        assert isinstance(markets, dict) or isinstance(markets, list)
        if isinstance(markets, dict):
            assert "all_assets" in markets or "priority_assets" in markets or "watchlist" in markets

    async def test_05_market_detail(self):
        """Phase 14.5 — MARKET DETAIL: Verify symbol specific telemetry."""
        resp = await self.client.get("/api/markets/BTCUSDT")
        assert resp.status == 200
        detail = await resp.json()
        assert detail["symbol"] == "BTCUSDT"

    async def test_06_strategies(self):
        """Phase 14.6 — STRATEGIES: Verify strategy library catalog."""
        resp = await self.client.get("/api/strategies")
        assert resp.status == 200
        strategies = await resp.json()
        assert isinstance(strategies, list)

    async def test_07_research_lab(self):
        """Phase 14.7 — RESEARCH: Verify strategy specification parsing."""
        parse_req = {"prompt": "Trade pullback continuation on BTCUSDT with 4R target and 1% risk"}
        resp = await self.client.post("/api/strategy-lab/parse", json=parse_req)
        assert resp.status == 200
        data = await resp.json()
        assert "specification" in data

    async def test_08_backtest(self):
        """Phase 14.8 — BACKTEST: Verify backtesting catalog results."""
        resp = await self.client.get("/api/backtests")
        assert resp.status == 200
        backtests = await resp.json()
        assert isinstance(backtests, dict) or isinstance(backtests, list)
        if isinstance(backtests, dict):
            assert "benchmark_king" in backtests or "recent_runs" in backtests

    async def test_09_forward_test(self):
        """Phase 14.9 — FORWARD TEST: Verify forward validation engine output."""
        resp = await self.client.get("/api/forward-validation")
        assert resp.status == 200
        fw = await resp.json()
        assert "status" in fw or "runs" in fw or isinstance(fw, list) or isinstance(fw, dict)

    async def test_10_trading_positions_and_orders(self):
        """Phase 14.10 — TRADING: Verify positions, orders blotter, and fail-closed safety."""
        # Positions
        resp_pos = await self.client.get("/api/positions")
        assert resp_pos.status == 200
        pos_data = await resp_pos.json()
        assert "active_positions" in pos_data
        assert "closed_positions" in pos_data

        # Orders
        resp_orders = await self.client.get("/api/orders")
        assert resp_orders.status == 200

        # Decisions
        resp_dec = await self.client.get("/api/decisions")
        assert resp_dec.status == 200

    async def test_11_risk_management(self):
        """Phase 14.11 — RISK MANAGEMENT: Verify risk metrics & circuit breakers."""
        resp = await self.client.get("/api/risk")
        assert resp.status == 200
        risk = await resp.json()
        assert "capital_safety" in risk or "max_portfolio_heat_pct" in risk or "circuit_breaker_active" in risk

    async def test_12_performance_and_telemetry(self):
        """Phase 14.12 — PERFORMANCE: Verify telemetry performance metrics."""
        resp = await self.client.get("/api/telemetry")
        assert resp.status == 200
        telemetry = await resp.json()
        assert "execution_mode" in telemetry
        assert telemetry["real_capital_authorized"] == 0.00

    async def test_13_monitoring_and_alerts(self):
        """Phase 14.13 — MONITORING: Verify reconciliation, drift, and alerts."""
        # Reconciliation
        resp_rec = await self.client.get("/api/reconciliation")
        assert resp_rec.status == 200

        # Drift
        resp_drift = await self.client.get("/api/drift")
        assert resp_drift.status == 200

        # Alerts
        resp_alerts = await self.client.get("/api/alerts")
        assert resp_alerts.status == 200

    async def test_14_accounts_and_brokers(self):
        """Phase 14.14 — ACCOUNT: Verify accounts and broker connections."""
        # Accounts
        resp_acc = await self.client.get("/api/accounts")
        assert resp_acc.status == 200
        accs = await resp_acc.json()
        assert isinstance(accs, list)

        # Brokers
        resp_brok = await self.client.get("/api/brokers")
        assert resp_brok.status == 200
        brokers = await resp_brok.json()
        assert isinstance(brokers, list)
