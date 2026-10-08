"""
Comprehensive Programmatic Acceptance Test Suite for STRATA Product Reality Upgrade.
Exercises every single route, endpoint, validation gate, authentication state,
and safety control in the platform.
"""

import pytest
from aiohttp.test_utils import TestClient, TestServer
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from web.server import PhaseRWebServer


@pytest.fixture
def supervisor():
    return AutonomousTradingSupervisor(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])


@pytest.fixture
def test_server(supervisor):
    return PhaseRWebServer(supervisor=supervisor)


@pytest.mark.asyncio
async def test_full_programmatic_product_journey(test_server):
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Engineering & admin interface
        resp = await client.get("/")
        assert resp.status == 200
        html = await resp.text()
        assert "Crypto Platform" in html
        assert "Android" in html
        assert "$0.00" in html

        # 2. Terminal app page
        resp_app = await client.get("/app")
        assert resp_app.status == 200
        app_html = await resp_app.text()
        assert "Crypto Platform" in app_html

        # 3. Dashboard redirect/view
        resp_dash = await client.get("/dashboard")
        assert resp_dash.status == 200

        # 4. Health telemetry endpoint
        resp_health = await client.get("/api/health")
        assert resp_health.status == 200
        h_data = await resp_health.json()
        assert h_data["real_capital_authorized"] == 0.00
        assert h_data["live_trading_status"] == "DISABLED_FAIL_CLOSED"
        assert h_data["execution_mode"] == "PAPER"

        # 5. Version & contract hash
        resp_ver = await client.get("/api/version")
        assert resp_ver.status == 200
        v_data = await resp_ver.json()
        assert v_data["king_contract_hash"] == "8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098"

        # 6. Auth Registration: Invalid (passwords do not match)
        resp_reg_fail = await client.post("/api/auth/register", json={
            "name": "Institutional QA",
            "email": "qa@strata.fund",
            "password": "Password12345!",
            "password_confirmation": "WrongPassword12345!",
        })
        assert resp_reg_fail.status == 400
        assert "error" in (await resp_reg_fail.json())

        # 7. Auth Registration: Valid
        resp_reg_ok = await client.post("/api/auth/register", json={
            "name": "Institutional QA",
            "email": "qa@strata.fund",
            "password": "Password12345!",
            "password_confirmation": "Password12345!",
        })
        assert resp_reg_ok.status == 200
        reg_data = await resp_reg_ok.json()
        assert reg_data["status"] == "registered"
        token = reg_data["token"]
        assert token is not None

        # 8. Auth Login: Bad password
        resp_bad_login = await client.post("/api/auth/login", json={
            "email": "qa@strata.fund",
            "password": "WrongPassword!",
        })
        assert resp_bad_login.status == 401

        # 9. Auth Login: Correct credentials
        resp_login = await client.post("/api/auth/login", json={
            "email": "qa@strata.fund",
            "password": "Password12345!",
        })
        assert resp_login.status == 200
        login_data = await resp_login.json()
        auth_token = login_data["token"]

        # 10. Auth /me
        resp_me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp_me.status == 200
        me_data = await resp_me.json()
        assert me_data["name"] == "Institutional QA"
        assert me_data["email"] == "qa@strata.fund"

        # 11. Markets list
        resp_mkts = await client.get("/api/markets")
        assert resp_mkts.status == 200
        mkts_data = await resp_mkts.json()
        assert len(mkts_data["all_assets"]) >= 4
        assert len(mkts_data["priority_assets"]) >= 1

        # 12. Asset Detail BTCUSDT
        resp_btc = await client.get("/api/markets/BTCUSDT")
        assert resp_btc.status == 200
        btc_data = await resp_btc.json()
        assert btc_data["symbol"] == "BTCUSDT"
        assert len(btc_data["timeframes"]) == 7

        # 13. Watchlist toggle
        resp_wl = await client.post("/api/markets/watchlist", json={"symbol": "SOLUSDT"})
        assert resp_wl.status == 200
        wl_data = await resp_wl.json()
        assert "SOLUSDT" in wl_data["watchlist"]

        # 14. Billing status
        resp_bill = await client.get("/api/billing")
        assert resp_bill.status == 200
        bill_data = await resp_bill.json()
        assert bill_data["status"]["is_launch_period"] is True
        assert bill_data["status"]["current_charge_usd"] == 0.00

        # 15. Billing plan update
        resp_plan = await client.post("/api/billing/plan", json={"tier": "INSTITUTIONAL"})
        assert resp_plan.status == 200
        plan_res = await resp_plan.json()
        assert plan_res["current_plan"]["tier"] == "INSTITUTIONAL"

        # 16. Strategies list
        resp_strats = await client.get("/api/strategies")
        assert resp_strats.status == 200
        strats_data = await resp_strats.json()
        assert len(strats_data) >= 7

        # 17. Strategy Lab Parse
        resp_parse = await client.post("/api/strategy-lab/parse", json={
            "prompt": "Create a BTC swing strategy using market structure, pullbacks and minimum 4R."
        })
        assert resp_parse.status == 200
        parse_res = await resp_parse.json()
        assert "BTCUSDT" in parse_res["specification"]["assets"]

        # 18. Strategy Lab Copilot Chat
        resp_copilot = await client.post("/api/strategy-lab/copilot", json={
            "prompt": "Explain the 7-timeframe ladder and how risk is controlled."
        })
        assert resp_copilot.status == 200
        copilot_res = await resp_copilot.json()
        assert "reply" in copilot_res
        assert "$0.00" in copilot_res["disclaimer"]

        # 19. Backtests blotter
        resp_bt = await client.get("/api/backtests")
        assert resp_bt.status == 200
        bt_data = await resp_bt.json()
        assert bt_data["benchmark_king"]["total_trades"] == 9608

        # 20. Forward validation
        resp_fv = await client.get("/api/forward-validation")
        assert resp_fv.status == 200
        fv_data = await resp_fv.json()
        assert fv_data["environments"]["LIVE"]["authorized_capital_usd"] == 0.00

        # 21. Risk Center
        resp_risk = await client.get("/api/risk")
        assert resp_risk.status == 200
        risk_res = await resp_risk.json()
        assert risk_res["max_trade_risk_pct"] <= 1.00
        assert risk_res["max_portfolio_heat_pct"] <= 3.00

        # 22. Accounts list
        resp_accs = await client.get("/api/accounts")
        assert resp_accs.status == 200

        # 23. Brokers list
        resp_brks = await client.get("/api/brokers")
        assert resp_brks.status == 200
        brks_data = await resp_brks.json()
        assert len(brks_data) == 3

        # 24. Positions blotter
        resp_pos = await client.get("/api/positions")
        assert resp_pos.status == 200

        # 25. Orders blotter
        resp_ords = await client.get("/api/orders")
        assert resp_ords.status == 200

        # 26. Decisions blotter
        resp_decs = await client.get("/api/decisions")
        assert resp_decs.status == 200

        # 27. Reconciliation
        resp_recon = await client.get("/api/reconciliation")
        assert resp_recon.status == 200
        recon_data = await resp_recon.json()
        assert recon_data["is_reconciled"] is True

        # 28. Drift
        resp_drift = await client.get("/api/drift")
        assert resp_drift.status == 200

        # 29. Alerts
        resp_alerts = await client.get("/api/alerts")
        assert resp_alerts.status == 200

        # 30. Agent Pause / Resume (Emergency Halt)
        resp_pause = await client.post("/api/agent/pause")
        assert resp_pause.status == 200
        assert (await resp_pause.json())["status"] == "PAUSED"

        resp_resume = await client.post("/api/agent/resume")
        assert resp_resume.status == 200
        assert (await resp_resume.json())["status"] == "OBSERVING"

        # 31. Auth Logout
        resp_logout = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp_logout.status == 200

        # 32. Verify session revoked
        resp_revoked = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp_revoked.status == 401
