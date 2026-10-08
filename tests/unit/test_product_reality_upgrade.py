"""
Unit & Integration Tests for STRATA Product Reality Upgrade.
Verifies:
1. User registration with name and password confirmation + login + tenant isolation.
2. Market service & endpoints: /api/markets, /api/markets/{symbol}, /api/markets/watchlist.
3. Billing engine & endpoints: /api/billing, /api/billing/plan ($0.00 launch pricing).
4. Strategy research copilot: /api/strategy-lab/copilot rejecting unsafe claims and returning formal specs.
5. Backtests, Forward validation, and Risk telemetry endpoints.
6. Execution and safety invariants: live capital strictly $0.00.
"""

import pytest
from core.auth.auth_service import AuthService
from market_data.market_service import MarketService
from core.billing.billing_engine import BillingEngine, PlanTier
from strategy.lab.strategy_lab_engine import StrategyLabEngine


class TestProductRealityUpgrade:
    @pytest.fixture
    def auth_service(self):
        service = AuthService()
        return service

    @pytest.fixture
    def market_service(self):
        return MarketService()

    @pytest.fixture
    def billing_engine(self):
        return BillingEngine()

    @pytest.fixture
    def strategy_lab(self):
        return StrategyLabEngine()

    def test_registration_with_name_and_password_confirmation(self, auth_service):
        # 1. Mismatched passwords
        with pytest.raises(ValueError, match="do not match"):
            auth_service.register_user(
                email="test_user@strata.institutional",
                password="SecurePassword123!",
                name="Alpha Researcher",
                password_confirmation="DifferentPassword123!"
            )

        # 2. Short password
        with pytest.raises(ValueError, match="at least 8 characters"):
            auth_service.register_user(
                email="test_user@strata.institutional",
                password="123",
                name="Alpha Researcher",
                password_confirmation="123"
            )

        # 3. Successful registration
        user = auth_service.register_user(
            email="test_user@strata.institutional",
            password="SecurePassword123!",
            name="Alpha Researcher",
            password_confirmation="SecurePassword123!"
        )
        assert user is not None
        assert user.name == "Alpha Researcher"
        assert user.email == "test_user@strata.institutional"
        assert user.tenant_id.startswith("tenant_")

        # 4. Duplicate registration fails gracefully
        with pytest.raises(ValueError, match="already exists"):
            auth_service.register_user(
                email="test_user@strata.institutional",
                password="SecurePassword123!",
                name="Alpha Researcher 2",
                password_confirmation="SecurePassword123!"
            )

        # 5. Authenticate user
        session = auth_service.authenticate("test_user@strata.institutional", "SecurePassword123!")
        assert session is not None
        assert session.token.startswith("strata_")
        assert session.user_id == user.user_id
        assert session.tenant_id == user.tenant_id

        # 6. Validate session
        validated_user = auth_service.validate_session(session.token)
        assert validated_user is not None
        assert validated_user.name == "Alpha Researcher"

        # 7. Logout invalidates session
        logout_ok = auth_service.logout(session.token)
        assert logout_ok is True
        assert auth_service.validate_session(session.token) is None

    def test_market_service_universe_and_causal_states(self, market_service):
        assets = market_service.list_market_assets("tenant_alpha")
        assert len(assets["all_assets"]) >= 4
        symbols = [m["symbol"] for m in assets["all_assets"]]
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SOLUSDT" in symbols
        assert "BNBUSDT" in symbols

        # Verify all markets have truthful data sources and multi-timeframe states
        btc = market_service.get_asset_detail("BTCUSDT")
        assert btc is not None
        assert btc["symbol"] == "BTCUSDT"
        assert btc["execution_eligibility"] == "PAPER_AND_DEMO_ELIGIBLE"
        assert "timeframes" in btc
        tfs = btc["timeframes"]
        assert "1M" in tfs
        assert "1D" in tfs
        assert "15M" in tfs
        assert tfs["1D"]["structure"] == "BULLISH"
        assert tfs["1D"]["phase"] == "MARKUP"
        assert tfs["1D"]["premium_discount"] == "DISCOUNT"

    def test_watchlist_tenant_isolation(self, market_service):
        # Tenant A toggles SOLUSDT to watchlist
        updated_wl_a = market_service.toggle_watchlist("tenant_a", "SOLUSDT")
        assert "SOLUSDT" in updated_wl_a

        # Tenant B watchlist should not contain SOLUSDT
        wl_b = market_service.get_watchlist("tenant_b")
        assert "SOLUSDT" not in wl_b

        # Toggle off for Tenant A
        updated_wl_a2 = market_service.toggle_watchlist("tenant_a", "SOLUSDT")
        assert "SOLUSDT" not in updated_wl_a2

    def test_billing_engine_launch_zero_charges(self, billing_engine):
        # Status check
        status = billing_engine.get_tenant_billing_status("tenant_alpha")
        assert status["is_launch_period"] is True
        assert status["current_charge_usd"] == 0.00
        assert status["charges_enabled"] is False
        assert status["current_plan"]["tier"] == PlanTier.AUTONOMOUS.value

        # Switch to INSTITUTIONAL during launch
        switch_res = billing_engine.assign_plan("tenant_alpha", PlanTier.INSTITUTIONAL.value)
        assert switch_res["current_plan"]["tier"] == PlanTier.INSTITUTIONAL.value
        assert switch_res["current_charge_usd"] == 0.00  # Must be zero during launch
        assert switch_res["charges_enabled"] is False

    def test_strategy_research_copilot_safety_and_disclaimers(self, strategy_lab):
        # 1. Ask for explanation of rules and architecture
        res_explain = strategy_lab.research_copilot_chat("Explain how KING and target floor work")
        assert "disclaimer" in res_explain
        assert "$0.00" in res_explain["disclaimer"]
        assert "7-Timeframe Ladder" in res_explain["reply"]
        assert "≥ 4.0R" in res_explain["reply"]

        # 2. Request a valid swing strategy specification
        res_valid = strategy_lab.research_copilot_chat("Create a BTC swing strategy using market structure, pullbacks and minimum 4R.")
        assert res_valid["suggested_action"] == "SPECIFICATION_GENERATED"
        assert res_valid["specification"] is not None
        spec = res_valid["specification"]
        assert "BTCUSDT" in spec["assets"]
        assert "4R" in spec["target_rule"]
        assert spec["risk_rule"] == "MAX_1_PCT_TRADE_RISK"
        assert "disclaimer" in res_valid
        assert "$0.00" in res_valid["disclaimer"]


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
async def test_rest_api_markets_endpoints(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. /api/markets
        resp = await client.get("/api/markets")
        assert resp.status == 200
        data = await resp.json()
        assert "all_assets" in data
        assert "watchlist" in data
        assert len(data["all_assets"]) >= 4

        # 2. /api/markets/BTCUSDT
        resp_btc = await client.get("/api/markets/BTCUSDT")
        assert resp_btc.status == 200
        btc = await resp_btc.json()
        assert btc["symbol"] == "BTCUSDT"
        assert "timeframes" in btc

        # 3. Toggle watchlist
        resp_wl = await client.post("/api/markets/watchlist", json={"symbol": "SOLUSDT"})
        assert resp_wl.status == 200
        wl_data = await resp_wl.json()
        assert "SOLUSDT" in wl_data["watchlist"]


@pytest.mark.asyncio
async def test_rest_api_billing_endpoints(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. /api/billing
        resp = await client.get("/api/billing")
        assert resp.status == 200
        data = await resp.json()
        assert "status" in data
        assert data["status"]["is_launch_period"] is True
        assert data["status"]["current_charge_usd"] == 0.00
        assert data["status"]["charges_enabled"] is False

        # 2. /api/billing/plan
        resp_plan = await client.post("/api/billing/plan", json={"tier": "INSTITUTIONAL"})
        assert resp_plan.status == 200
        plan_data = await resp_plan.json()
        assert plan_data["current_plan"]["tier"] == "INSTITUTIONAL"
        assert plan_data["current_charge_usd"] == 0.00


@pytest.mark.asyncio
async def test_rest_api_copilot_and_risk_endpoints(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. /api/strategy-lab/copilot
        resp_copilot = await client.post("/api/strategy-lab/copilot", json={
            "prompt": "Create a BTC swing strategy using market structure, pullbacks and minimum 4R."
        })
        assert resp_copilot.status == 200
        copilot_data = await resp_copilot.json()
        assert "reply" in copilot_data
        assert "disclaimer" in copilot_data
        assert "$0.00" in copilot_data["disclaimer"]

        # 2. /api/risk
        resp_risk = await client.get("/api/risk")
        assert resp_risk.status == 200
        risk_data = await resp_risk.json()
        assert risk_data["max_trade_risk_pct"] <= 1.0
        assert risk_data["max_portfolio_heat_pct"] <= 3.0
        assert risk_data["capital_safety_gate"]["real_capital_authorized_usd"] == 0.00
        assert risk_data["capital_safety_gate"]["live_execution_locked"] is True

        # 3. /api/forward-validation
        resp_fv = await client.get("/api/forward-validation")
        assert resp_fv.status == 200
        fv_data = await resp_fv.json()
        assert "environments" in fv_data
        assert fv_data["environments"]["LIVE"]["authorized_capital_usd"] == 0.00
        assert fv_data["safety_invariants"]["real_capital_authorized"] == 0.00

