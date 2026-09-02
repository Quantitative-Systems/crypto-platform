"""
Regression test for LiveTradingEngine.on_bar_closed candidate execution and AccountState construction.
"""

import pytest
from unittest.mock import patch

from production.live_trader import LiveTradingEngine
from execution_gateway.gateways.paper_gateway import PaperGateway
from market_intelligence.primitives import Candle
from strategy_engine.contracts.trade_plan import TradePlanPayload


@pytest.mark.anyio
async def test_live_trader_on_bar_closed_candidate_execution_regression(tmp_path):
    """
    Verifies that when StrategyCoordinator generates a trade plan,
    LiveTradingEngine constructs AccountState correctly with canonical fields
    and advances through RiskCoordinator, PortfolioCoordinator, and OrderManager without raising TypeError.
    """
    db_path = str(tmp_path / "test_live_state.db")
    gateway = PaperGateway(initial_balance=100_000.0)
    await gateway.connect()

    engine = LiveTradingEngine(
        gateway=gateway,
        initial_balance=100_000.0,
        state_db_path=db_path
    )
    await engine.start()

    # Create dummy candle streams
    candles = [
        Candle(timestamp=1700000000 + i * 3600, open=60000.0, high=60500.0, low=59500.0, close=60200.0, volume=100.0)
        for i in range(20)
    ]

    # Mock candidate trade plan returned by StrategyCoordinator
    dummy_plan = TradePlanPayload(
        hypothesis_id="HYP_UNIFIED",
        trade_plan_id="test_plan_001",
        symbol="BTC/USDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1700000000 + 19 * 3600,
        entry_price=60000.0,
        stop_invalidation_price=59000.0,
        target_price=65000.0,
        raw_rr=5.0,
        status="RISK_GATE"
    )

    with patch.object(engine.strategy_coordinator, "evaluate", return_value=[dummy_plan]):
        executed_plans = await engine.on_bar_closed(
            symbol="BTC/USDT",
            htf_candles=candles,
            mtf_candles=candles,
            ltf_candles=candles,
            current_atr=500.0
        )

        assert len(executed_plans) == 1
        plan = executed_plans[0]
        assert plan.trade_plan_id == "test_plan_001"
        assert plan.is_approved is True
        assert plan.allocated_units > 0
        assert plan.entry_price == 60000.0
        assert plan.stop_loss_price == 59000.0
        assert plan.target_price == 65000.0

    await engine.stop()
