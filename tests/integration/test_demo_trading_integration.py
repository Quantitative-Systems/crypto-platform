"""End-to-End Integration Tests for Demo & Testnet Broker Trading Harness.

Verifies:
- Live Demo Harness lifecycle on Binance Futures & Bybit V5 adapters.
- Complete execution path: OrderIntent -> Risk Firewall -> OMS -> Adapter -> StateReconciler -> SQLite Ledger.
- Non-custodial permission auditing on adapter connection.
- Automated reconciliation matching OMS state against exchange actuals.
"""
import os
import pytest
import time

from crypto_platform.core.domain import ExecutionUrgency, OperatingMode, OrderIntent
from crypto_platform.demo_trading.harness import DemoTradingHarness
from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
from crypto_platform.exchange_adapters.bybit_adapter import BybitAdapter
from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy


@pytest.mark.anyio
async def test_demo_trading_harness_binance_flow(tmp_path):
    db_file = os.path.join(str(tmp_path), "demo_binance.db")
    adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=True)

    harness = DemoTradingHarness(
        adapter=adapter,
        db_path=db_file,
        account_id="acc_demo_binance",
        initial_equity=100_000.0,
    )

    strat = TrendBreakoutStrategy("strat_demo_eth", horizon="INTRADAY", supported_symbols=["ETHUSDT"])
    harness.register_strategy(strat)

    # 1. Initialize harness
    init_ok = await harness.initialize(credentials={"api_key": "TEST_KEY", "api_secret": "TEST_SECRET"})
    assert init_ok is True
    assert harness.current_equity == 100_000.0
    assert os.path.exists(db_file)

    # 2. Execute a valid OrderIntent
    intent = OrderIntent(
        intent_id="int_001",
        strategy_id="strat_demo_eth",
        tenant_id="t_demo",
        account_id="acc_demo_binance",
        symbol="ETHUSDT",
        direction=1,
        target_size=1.5,
        urgency=ExecutionUrgency.NORMAL,
        limit_price=2500.0,
        stop_price=2450.0,
        target_price=2600.0,
        horizon="INTRADAY",
        created_at_ms=int(time.time() * 1000),
        signal_reason="Donchian 20-bar breakout",
    )

    order = await harness.execute_intent(intent)
    assert order is not None
    assert order.symbol == "ETHUSDT"
    assert harness.funnel.order_intents == 1
    assert harness.funnel.oms_acceptances == 1
    assert harness.funnel.simulator_submissions == 1

    # 3. Verify state reconciliation matches
    rec = await harness.reconcile()
    assert rec["orders"]["clean"] is True
    assert rec["positions"]["clean"] is True

    # 4. Verify summary output
    summary = harness.get_summary()
    assert summary["mode"] == OperatingMode.DEMO.value
    assert summary["venue"] == "binance_futures"
    assert summary["total_orders_submitted"] == 1
    assert len(summary["recent_audit_records"]) == 1


@pytest.mark.anyio
async def test_demo_trading_harness_bybit_flow(tmp_path):
    db_file = os.path.join(str(tmp_path), "demo_bybit.db")
    adapter = BybitAdapter(testnet=True, mock_mode=True)

    harness = DemoTradingHarness(
        adapter=adapter,
        db_path=db_file,
        account_id="acc_demo_bybit",
        initial_equity=50_000.0,
    )

    init_ok = await harness.initialize()
    assert init_ok is True
    assert harness.current_equity == 50_000.0

    # Execute intent
    intent = OrderIntent(
        intent_id="int_bybit_1",
        strategy_id="strat_demo_sol",
        tenant_id="t_demo",
        account_id="acc_demo_bybit",
        symbol="SOLUSDT",
        direction=1,
        target_size=10.0,
        urgency=ExecutionUrgency.NORMAL,
        limit_price=150.0,
        stop_price=140.0,
        target_price=170.0,
        horizon="SWING",
        created_at_ms=int(time.time() * 1000),
        signal_reason="Trend breakout",
    )

    order = await harness.execute_intent(intent)
    assert order is not None
    assert harness.funnel.oms_acceptances == 1

    rec = await harness.reconcile()
    assert rec["orders"]["clean"] is True
