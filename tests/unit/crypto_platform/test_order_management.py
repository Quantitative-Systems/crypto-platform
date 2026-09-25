"""Tests for Order Management System and Lifecycle State Machine."""
import pytest
from crypto_platform.core.domain import (
    ExecutionOrder,
    ExecutionUrgency,
    Fill,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskDecision,
    TimeInForce,
)
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.order_management.router import OrderRouter
from crypto_platform.order_management.state_machine import OrderStateMachine


def test_order_state_machine_valid_transitions():
    order = ExecutionOrder(
        order_id="o1",
        client_order_id="c1",
        tenant_id="t1",
        account_id="a1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=1.0,
        price=60_000.0,
    )
    assert order.status == OrderStatus.CREATED

    OrderStateMachine.transition(order, OrderStatus.RISK_CHECKED)
    assert order.status == OrderStatus.RISK_CHECKED

    OrderStateMachine.transition(order, OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED

    OrderStateMachine.transition(order, OrderStatus.ACKNOWLEDGED)
    assert order.status == OrderStatus.ACKNOWLEDGED

    OrderStateMachine.transition(order, OrderStatus.PARTIALLY_FILLED)
    assert order.status == OrderStatus.PARTIALLY_FILLED

    OrderStateMachine.transition(order, OrderStatus.FILLED)
    assert order.status == OrderStatus.FILLED


def test_order_state_machine_illegal_transition():
    order = ExecutionOrder(
        order_id="o1",
        client_order_id="c1",
        tenant_id="t1",
        account_id="a1",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=1.0,
        price=60_000.0,
        status=OrderStatus.FILLED,
    )
    # Cannot transition from FILLED to SUBMITTED
    with pytest.raises(ValueError, match="Illegal order transition"):
        OrderStateMachine.transition(order, OrderStatus.SUBMITTED)


def test_order_router_idempotent_cids():
    cid1 = OrderRouter.generate_client_order_id("tenant_a", "acct_01", "BTCUSDT", "strat_01")
    cid2 = OrderRouter.generate_client_order_id("tenant_a", "acct_01", "BTCUSDT", "strat_01")
    assert len(cid1) <= 32
    assert cid1 != cid2  # Unique nonces


def test_oms_position_tracking_and_pnl():
    oms = OrderManagementSystem()
    intent = OrderIntent(
        intent_id="i1",
        strategy_id="s1",
        tenant_id="t1",
        account_id="a1",
        symbol="BTCUSDT",
        direction=1,
        target_size=1.0,
        limit_price=60_000.0,
    )
    decision = RiskDecision(approved=True, reason="PASS")
    order = oms.create_order_from_intent(intent, decision)
    assert order.status == OrderStatus.RISK_CHECKED

    # 1. Fill buy order at 60,000
    fill1 = Fill(
        fill_id="f1",
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        price=60_000.0,
        quantity=1.0,
        fee=6.0,
        fee_asset="USDT",
        is_maker=True,
    )
    oms.register_fill(fill1, "a1")
    assert order.status == OrderStatus.FILLED

    positions = oms.get_positions("a1")
    assert "BTCUSDT" in positions
    pos = positions["BTCUSDT"]
    assert pos.size == 1.0
    assert pos.direction == 1
    assert pos.entry_price == 60_000.0

    # 2. Fill partial sell order (0.5 BTC) at 62,000 (+2,000/BTC gain)
    fill2 = Fill(
        fill_id="f2",
        order_id="o2",
        client_order_id="c2",
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        price=62_000.0,
        quantity=0.5,
        fee=3.1,
        fee_asset="USDT",
        is_maker=True,
    )
    oms.register_fill(fill2, "a1")
    pos = oms.get_positions("a1")["BTCUSDT"]
    assert pos.size == 0.5
    # Realized PnL: (62,000 - 60,000) * 0.5 = 1,000 USDT
    assert pos.realized_pnl == 1_000.0


def test_order_router_post_only():
    intent = OrderIntent(
        intent_id="i_po",
        strategy_id="s_po",
        tenant_id="t1",
        account_id="a1",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        urgency=ExecutionUrgency.LOW,
        limit_price=64_000.0,
    )
    decision = RiskDecision(approved=True, reason="PASS")
    order = OrderRouter.route_intent(intent, decision, "binance")
    assert order.order_type == OrderType.POST_ONLY
    assert order.time_in_force == TimeInForce.PO
    assert order.price == 64_000.0

