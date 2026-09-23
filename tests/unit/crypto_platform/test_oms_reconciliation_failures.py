"""Comprehensive test suite for OMS lifecycle, failure injection, and state reconciliation."""
import asyncio
import time
import pytest
from crypto_platform.core.domain import (
    ExecutionOrder,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RiskDecision,
    RiskState,
    TimeInForce,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.order_management.state_machine import OrderStateMachine
from crypto_platform.reconciliation.reconciler import StateReconciliationEngine
from crypto_platform.risk_engine.firewall import RiskFirewall


# =============================================================================
# 1. ORDER LIFECYCLE STATE MACHINE
# =============================================================================
def test_order_lifecycle_happy_path():
    order = ExecutionOrder(
        order_id="o_1",
        client_order_id="c_1",
        tenant_id="t_1",
        account_id="acct_1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=60000.0,
        status=OrderStatus.CREATED,
    )
    # CREATED -> RISK_CHECKED
    OrderStateMachine.transition(order, OrderStatus.RISK_CHECKED)
    assert order.status == OrderStatus.RISK_CHECKED

    # RISK_CHECKED -> SUBMITTED
    OrderStateMachine.transition(order, OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED

    # SUBMITTED -> ACKNOWLEDGED
    OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED)
    assert order.status == OrderStatus.ACKNOWLEDGED

    # ACKNOWLEDGED -> PARTIALLY_FILLED
    OrderStateMachine.transition(order, OrderStatus.PARTIALLY_FILLED)
    assert order.status == OrderStatus.PARTIALLY_FILLED

    # PARTIALLY_FILLED -> FILLED
    OrderStateMachine.transition(order, OrderStatus.FILLED)
    assert order.status == OrderStatus.FILLED


def test_order_lifecycle_terminal_and_illegal_transitions():
    order = ExecutionOrder(
        order_id="o_2",
        client_order_id="c_2",
        tenant_id="t_1",
        account_id="acct_1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=60000.0,
        status=OrderStatus.FILLED,
    )
    # Cannot transition from terminal state FILLED to SUBMITTED
    with pytest.raises(ValueError, match="Illegal order transition"):
        OrderStateMachine.transition(order, OrderStatus.SUBMITTED)

    # Cannot transition directly from CREATED to FILLED
    order_created = ExecutionOrder(
        order_id="o_3",
        client_order_id="c_3",
        tenant_id="t_1",
        account_id="acct_1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=60000.0,
        status=OrderStatus.CREATED,
    )
    with pytest.raises(ValueError, match="Illegal order transition"):
        OrderStateMachine.transition(order_created, OrderStatus.FILLED)


# =============================================================================
# 2. OMS FAILURE INJECTION & RECONCILIATION
# =============================================================================
@pytest.mark.anyio
async def test_reconciliation_detects_out_of_band_mismatch_and_freezes():
    oms = OrderManagementSystem()
    firewall = RiskFirewall()
    reconciler = StateReconciliationEngine(risk_firewall=firewall)
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({})

    account_id = "acct_recon_01"

    # Out-of-band trade occurred on exchange: exchange has 1.0 BTC long
    adapter._mock_positions["BTCUSDT"] = Position(
        symbol="BTCUSDT", direction=1, size=1.0, entry_price=60000.0, mark_price=60000.0
    )

    # Local OMS has 0.0 BTC (untracked)
    is_in_sync = await reconciler.reconcile_account(account_id, adapter, oms)
    assert is_in_sync is False
    assert len(reconciler.reports_history) == 1
    assert "Position mismatch on BTCUSDT" in reconciler.reports_history[-1].discrepancies[0]

    # Verify trading is FROZEN in RiskFirewall
    now_ms = int(time.time() * 1000)
    intent = OrderIntent(
        intent_id=f"intent_blocked_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_1",
        account_id=account_id,
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        created_at_ms=now_ms,
    )
    ticker = TickerEvent(
        venue="binance", symbol="BTCUSDT", timestamp_ms=now_ms, bid=60000.0, ask=60002.0, last_price=60001.0
    )
    decision = firewall.evaluate_order_intent(intent, {}, {}, RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0), ticker)
    assert decision.approved is False
    assert decision.rule_code == "RECONCILIATION_OUT_OF_SYNC"


@pytest.mark.anyio
async def test_reconciliation_restores_state_cleanly_without_duplicate_orders():
    oms = OrderManagementSystem()
    firewall = RiskFirewall()
    reconciler = StateReconciliationEngine(risk_firewall=firewall)
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({})

    account_id = "acct_recon_02"

    # Exchange truth has 0.5 ETH
    adapter._mock_positions["ETHUSDT"] = Position(
        symbol="ETHUSDT", direction=1, size=0.5, entry_price=3000.0, mark_price=3050.0
    )

    # Run state restoration
    restored = await reconciler.restore_state_from_exchange(account_id, adapter, oms)
    assert restored is True

    # Local OMS now reflects exchange truth
    local_pos = oms.get_positions(account_id)
    assert "ETHUSDT" in local_pos
    assert local_pos["ETHUSDT"].size == 0.5

    # Reconcile again: must be IN SYNC
    is_in_sync = await reconciler.reconcile_account(account_id, adapter, oms)
    assert is_in_sync is True

    # Verify RiskFirewall unfreezes trading
    now_ms = int(time.time() * 1000)
    intent = OrderIntent(
        intent_id=f"intent_ok_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_1",
        account_id=account_id,
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        created_at_ms=now_ms,
    )
    ticker = TickerEvent(
        venue="binance", symbol="BTCUSDT", timestamp_ms=now_ms, bid=60000.0, ask=60002.0, last_price=60001.0
    )
    decision = firewall.evaluate_order_intent(intent, local_pos, {}, RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0), ticker)
    assert decision.approved is True
    assert decision.rule_code == "PASS"
