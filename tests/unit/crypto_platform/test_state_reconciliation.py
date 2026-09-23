"""Tests for State Reconciliation Engine."""
import pytest
from crypto_platform.core.domain import ExecutionOrder, OrderSide, OrderStatus, OrderType, Position, TimeInForce
from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.reconciliation.reconciler import StateReconciliationEngine


@pytest.mark.anyio
async def test_reconciliation_clean_sync():
    engine = StateReconciliationEngine()
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({"api_key": "k", "api_secret": "s"})
    oms = OrderManagementSystem()

    # Both empty positions -> in sync
    in_sync = await engine.reconcile_account("acc_01", adapter, oms)
    assert in_sync is True
    assert len(engine.reports_history) == 1
    assert engine.reports_history[0].is_in_sync is True


@pytest.mark.anyio
async def test_reconciliation_detects_position_mismatch():
    engine = StateReconciliationEngine()
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({"api_key": "k", "api_secret": "s"})
    oms = OrderManagementSystem()

    # OMS thinks we have 1.0 BTC position
    oms._positions["acc_01"] = {
        "BTCUSDT": Position(symbol="BTCUSDT", direction=1, size=1.0, entry_price=60_000.0, mark_price=60_000.0)
    }
    # Exchange has 0 BTC position
    in_sync = await engine.reconcile_account("acc_01", adapter, oms)
    assert in_sync is False
    assert len(engine.reports_history[-1].discrepancies) > 0
    assert "Position mismatch on BTCUSDT" in engine.reports_history[-1].discrepancies[0]


@pytest.mark.anyio
async def test_reconciliation_detects_ghost_order():
    engine = StateReconciliationEngine()
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({"api_key": "k", "api_secret": "s"})
    oms = OrderManagementSystem()

    # Local OMS has an open submitted order, but exchange has none
    order = ExecutionOrder(
        order_id="o1",
        client_order_id="c_ghost_123",
        tenant_id="t1",
        account_id="acc_01",
        venue="binance_futures",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.5,
        price=60_000.0,
        status=OrderStatus.SUBMITTED,
    )
    oms._orders["acc_01"] = {"o1": order}

    in_sync = await engine.reconcile_account("acc_01", adapter, oms)
    assert in_sync is False
    assert any("Ghost orders" in d for d in engine.reports_history[-1].discrepancies)
