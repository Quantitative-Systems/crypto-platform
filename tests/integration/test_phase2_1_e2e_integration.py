"""
Phase 2.1 Forensic End-to-End Integration Test Suite.
Verifies the six critical user and system flows:
  Flow A: Market list -> market detail -> timeframe state.
  Flow B: Strategy list -> strategy parsing -> rule validation.
  Flow C: Backtest submission -> job/result retrieval.
  Flow D: Paper position -> risk validation -> position/order display.
  Flow E: Monitoring API -> alert rendering.
  Flow F: Backend unavailable / invalid requests -> safe, truthful error handling.
"""

import pytest
from aiohttp.test_utils import TestClient, TestServer
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.safety.safety_gate import SAFETY_GATE, FatalSafetyError
from execution.king.king_engine_contract import KingEngineProtectionGuard
from web.server import PhaseRWebServer


@pytest.fixture
def supervisor():
    return AutonomousTradingSupervisor(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])


@pytest.fixture
def test_server(supervisor):
    return PhaseRWebServer(supervisor=supervisor)


@pytest.mark.asyncio
async def test_flow_a_markets_and_timeframe_state(test_server):
    """Flow A: Market list -> market detail -> timeframe state."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Fetch market list
        resp = await client.get("/api/markets")
        assert resp.status == 200
        data = await resp.json()
        assert "all_assets" in data
        assert "priority_assets" in data
        symbols = [a["symbol"] for a in data["all_assets"]]
        for admitted in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
            assert admitted in symbols

        # 2. Fetch specific market detail
        detail_resp = await client.get("/api/markets/BTCUSDT")
        assert detail_resp.status == 200
        detail = await detail_resp.json()
        assert detail["symbol"] == "BTCUSDT"
        assert "timeframes" in detail
        timeframes = detail["timeframes"]
        # Confirm 7 timeframes present
        expected_tfs = ["1M", "1W", "1D", "4H", "1H", "15M", "3M"]
        for tf in expected_tfs:
            assert tf in timeframes
            assert "structure" in timeframes[tf]
            assert "premium_discount" in timeframes[tf]


@pytest.mark.asyncio
async def test_flow_b_strategy_list_parsing_and_rule_validation(test_server):
    """Flow B: Strategy list -> strategy parsing -> rule validation."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Fetch strategy list
        resp = await client.get("/api/strategies")
        assert resp.status == 200
        strategies = await resp.json()
        assert isinstance(strategies, list)
        assert len(strategies) >= 3
        king_strat = next((s for s in strategies if "KING" in s.get("name", "") or s.get("strategy_id") == "STRATA_KING_ENGINE"), None)
        assert king_strat is not None
        assert "4.0R" in king_strat["target_logic"] or king_strat.get("target_floor_r", 4.0) >= 4.0
        assert king_strat["risk_per_trade_pct"] <= 1.0

        # 2. Strategy parsing via natural language
        parse_resp = await client.post("/api/strategy-lab/parse", json={
            "prompt": "Create an ETH pullback swing continuation strategy with minimum 4.2R target floor and 0.8% risk."
        })
        assert parse_resp.status == 200
        parse_data = await parse_resp.json()
        spec = parse_data["specification"]
        assert "ETHUSDT" in spec["assets"]
        assert "4" in spec["target_rule"]
        assert "1" in spec["risk_rule"]

        # 3. Strategy evaluation
        eval_resp = await client.post("/api/strategy-lab/evaluate", json={
            "specification": spec
        })
        assert eval_resp.status == 200
        eval_data = await eval_resp.json()
        assert "verdict" in eval_data
        assert "metrics" in eval_data


@pytest.mark.asyncio
async def test_flow_c_backtest_and_forward_validation_retrieval(test_server):
    """Flow C: Backtest benchmark & forward validation retrieval."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Retrieve backtests endpoint
        resp = await client.get("/api/backtests")
        assert resp.status == 200
        result = await resp.json()
        assert "benchmark_king" in result
        benchmark = result["benchmark_king"]

        # 2. Verify reconciled metrics in benchmark
        assert benchmark["total_trades"] == 2942
        assert benchmark["unfiltered_trades"] == 9608
        assert benchmark["expectancy_r"] == 0.8885
        assert benchmark["profit_factor"] == 4.918
        assert benchmark["win_rate"] == 0.672
        assert benchmark["unfiltered_expectancy_r"] == 0.5781
        assert benchmark["unfiltered_profit_factor"] == 2.352
        assert benchmark["unfiltered_win_rate"] == 0.493

        # 3. Retrieve forward validation
        fv_resp = await client.get("/api/forward-validation")
        assert fv_resp.status == 200
        fv_data = await fv_resp.json()
        envs = fv_data["environments"]
        assert envs["HISTORICAL"]["trades_evaluated"] == 2942
        assert envs["HISTORICAL"]["expectancy_r"] == 0.8885
        assert envs["HISTORICAL_UNFILTERED"]["trades_evaluated"] == 9608
        assert envs["HISTORICAL_UNFILTERED"]["expectancy_r"] == 0.5781
        assert envs["OOS"]["trades_evaluated"] == 1665
        assert envs["OOS"]["expectancy_r"] == 0.8097
        assert envs["OOS"]["profit_factor"] == 4.024
        assert envs["LIVE"]["authorized_capital_usd"] == 0.00


@pytest.mark.asyncio
async def test_flow_d_paper_position_and_risk_validation(test_server):
    """Flow D: Paper position -> risk validation -> position/order display."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Risk parameters
        risk_resp = await client.get("/api/risk")
        assert risk_resp.status == 200
        risk_data = await risk_resp.json()
        assert risk_data["max_trade_risk_pct"] <= 1.0
        assert risk_data["max_portfolio_heat_pct"] <= 3.0
        assert risk_data["capital_safety_gate"]["real_capital_authorized_usd"] == 0.0

        # 2. Programmatic Safety Gate Invariants
        # Reject live order intent
        with pytest.raises(FatalSafetyError):
            SAFETY_GATE.assert_order_allowed(
                notional_usd=1000.0,
                risk_pct=0.5,
                open_positions_count=0,
                is_live_order=True
            )

        # King Guard Invariant Verification
        guard = KingEngineProtectionGuard()
        # Sub-4R target rejected
        valid, reason = guard.verify_invariants(target_r=3.2, trade_risk=0.005, portfolio_heat=0.02, real_capital=0.0)
        assert valid is False
        assert "violates King floor" in reason

        # Excess risk (>1.0%) rejected
        valid_risk, reason_risk = guard.verify_invariants(target_r=4.5, trade_risk=0.02, portfolio_heat=0.02, real_capital=0.0)
        assert valid_risk is False
        assert "exceeds King limit" in reason_risk

        # Compliant paper trade accepted
        valid_compliant, _ = guard.verify_invariants(target_r=4.2, trade_risk=0.008, portfolio_heat=0.02, real_capital=0.0)
        assert valid_compliant is True

        # 3. Check blotter endpoints
        orders_resp = await client.get("/api/orders")
        assert orders_resp.status == 200
        orders = await orders_resp.json()
        assert isinstance(orders, list)

        pos_resp = await client.get("/api/positions")
        assert pos_resp.status == 200
        pos_data = await pos_resp.json()
        assert "active_positions" in pos_data
        assert "closed_positions" in pos_data


@pytest.mark.asyncio
async def test_flow_e_monitoring_and_alerts(test_server):
    """Flow E: Monitoring API -> alert rendering."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Health endpoint
        health_resp = await client.get("/api/health")
        assert health_resp.status == 200
        health = await health_resp.json()
        assert health["real_capital_authorized"] == 0.0
        assert health["live_trading_status"] == "DISABLED_FAIL_CLOSED"

        # 2. Status alias
        status_resp = await client.get("/api/status")
        assert status_resp.status == 200
        status_data = await status_resp.json()
        assert status_data["status"].upper() == "HEALTHY"

        # 3. Alerts endpoint
        alerts_resp = await client.get("/api/alerts")
        assert alerts_resp.status == 200
        alerts = await alerts_resp.json()
        assert isinstance(alerts, list)

        # 4. Telemetry endpoint
        telem_resp = await client.get("/api/telemetry")
        assert telem_resp.status == 200
        telem = await telem_resp.json()
        assert telem["real_capital_authorized"] == 0.0
        assert telem["live_trading_status"] == "DISABLED_FAIL_CLOSED"
        assert "system_health" in telem
        assert "simulated_equity_usd" in telem


@pytest.mark.asyncio
async def test_flow_f_backend_truthful_error_handling(test_server):
    """Flow F: Non-existent routes, non-admitted assets, and truthful error returns."""
    async with TestClient(TestServer(test_server.app)) as client:
        # 1. Request non-admitted asset
        bad_market_resp = await client.get("/api/markets/DOGEUSDT")
        assert bad_market_resp.status == 404
        bad_market_json = await bad_market_resp.json()
        assert "error" in bad_market_json

        # 2. Non-existent API endpoint
        bad_route_resp = await client.get("/api/unknown_endpoint")
        assert bad_route_resp.status == 404

        # 3. Unauthenticated request to protected me endpoint
        unauth_resp = await client.get("/api/auth/me")
        assert unauth_resp.status == 401
