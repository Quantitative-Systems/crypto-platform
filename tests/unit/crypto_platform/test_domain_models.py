"""Tests for Core Domain Models and Canonical Events."""
import pytest
import time
from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    ExecutionUrgency,
    Fill,
    OperatingMode,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RiskDecision,
    RiskState,
    Tenant,
    TimeInForce,
)
from crypto_platform.core.events import (
    CandleEvent,
    FundingRateEvent,
    OrderBookEvent,
    TickerEvent,
)


def test_domain_entities_instantiation():
    tenant = Tenant(tenant_id="t_001", name="Alpha Quant")
    assert tenant.tenant_id == "t_001"
    assert tenant.is_active is True

    intent = OrderIntent(
        intent_id="i_001",
        strategy_id="strat_trend_01",
        tenant_id=tenant.tenant_id,
        account_id="acc_001",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.5,
        urgency=ExecutionUrgency.NORMAL,
        limit_price=65000.0,
    )
    assert intent.direction == 1
    assert intent.limit_price == 65000.0

    order = ExecutionOrder(
        order_id="ord_001",
        client_order_id="c_001",
        tenant_id=tenant.tenant_id,
        account_id="acc_001",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.5,
        price=65000.0,
    )
    assert order.status == OrderStatus.CREATED

    fill = Fill(
        fill_id="f_001",
        order_id=order.order_id,
        client_order_id=order.client_order_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        price=65000.0,
        quantity=0.5,
        fee=6.5,
        fee_asset="USDT",
        is_maker=True,
    )
    assert fill.is_maker is True
    assert fill.fee == 6.5


def test_canonical_events():
    ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=int(time.time() * 1000),
        bid=65000.0,
        ask=65001.0,
        last_price=65000.5,
    )
    assert ticker.bid == 65000.0
    assert ticker.ask == 65001.0
