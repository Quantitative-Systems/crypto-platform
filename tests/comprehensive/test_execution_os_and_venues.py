"""
Comprehensive Test Suite: Execution OS, Algorithms & Multi-Venue Adapters.
Validates:
- OrderIntent contracts & integrity hashing
- Smart Order Router (SOR) venue auction selection
- 8 Institutional Execution Algorithms (Market, Limit, Passive, TWAP, VWAP, Iceberg, POV, Adaptive)
- Multi-Venue Paper Adapters (Binance, OKX, Bybit, Deribit)
- Ground-truth Order & Position Reconciliation
"""

import pytest
from execution_gateway.execution_os.order_intent import (
    OrderIntent,
    OrderSide,
    ExecutionAlgoType,
    TimeInForce,
)
from execution_gateway.execution_os.smart_order_router import SmartOrderRouter, VenueQuote
from execution_gateway.execution_os.execution_algorithms import ExecutionAlgoFactory
from execution_gateway.venues.paper_venue_adapters import (
    BinancePaperAdapter,
    OkxPaperAdapter,
    BybitPaperAdapter,
    DeribitPaperAdapter,
)


def test_order_intent_hashing():
    intent = OrderIntent(
        intent_id="INTENT-001",
        strategy_id="FAM-07-SOL",
        tenant_id="tenant-primary",
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        target_quantity=10.0,
        algo_type=ExecutionAlgoType.TWAP,
        limit_price=150.0,
    )
    h1 = intent.compute_hash()
    assert len(h1) == 64
    assert h1 == intent.compute_hash()


def test_smart_order_router_venue_auction():
    sor = SmartOrderRouter()
    intent = OrderIntent(
        intent_id="INTENT-SOR",
        strategy_id="FAM-07-SOL",
        tenant_id="tenant-primary",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        target_quantity=1.0,
    )
    quotes = {
        "BINANCE_PAPER": VenueQuote("BINANCE_PAPER", "BTCUSDT", 59990.0, 60000.0, 50.0, 50.0, 4.0, 1.5, 5.0),
        "OKX_PAPER": VenueQuote("OKX_PAPER", "BTCUSDT", 59980.0, 60010.0, 50.0, 50.0, 6.0, 2.0, 15.0),
    }
    decision = sor.route_order(intent, quotes)
    assert decision.selected_venue_id == "BINANCE_PAPER"
    assert decision.total_estimated_cost_bps < 10.0


def test_all_8_execution_algorithms():
    algos = [
        ExecutionAlgoType.MARKET,
        ExecutionAlgoType.LIMIT,
        ExecutionAlgoType.PASSIVE,
        ExecutionAlgoType.TWAP,
        ExecutionAlgoType.VWAP,
        ExecutionAlgoType.ICEBERG,
        ExecutionAlgoType.POV,
        ExecutionAlgoType.ADAPTIVE,
    ]

    for algo in algos:
        intent = OrderIntent(
            intent_id=f"INTENT-{algo.value}",
            strategy_id="FAM-07-SOL",
            tenant_id="tenant-primary",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            target_quantity=1.0,
            algo_type=algo,
            limit_price=60_000.0,
        )
        plan = ExecutionAlgoFactory.plan_execution(
            intent=intent,
            selected_venue="BINANCE_PAPER",
            current_market_price=60_000.0,
        )
        assert plan.slice_count >= 1
        assert len(plan.child_orders) >= 1
        assert sum(c.quantity for c in plan.child_orders) == pytest.approx(1.0, rel=1e-2)


def test_paper_venue_adapters_and_reconciliation():
    venues = [BinancePaperAdapter(), OkxPaperAdapter(), BybitPaperAdapter(), DeribitPaperAdapter()]
    for v in venues:
        assert v.connect() is True
        assert v.authenticate() is True
        assert v.is_connected is True
        assert v.is_authenticated is True

        # Place paper order
        order = v.place_order(symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity=0.2, price=60_000.0)
        assert order.status == "FILLED"
        assert order.filled_qty == 0.2

        # Check balances and positions
        bals = v.balances()
        assert "USDT" in bals
        assert bals["USDT"].total > 0

        positions = v.positions()
        assert len(positions) >= 1
        assert positions[0].symbol == "BTCUSDT"

        # Check reconciliation
        internal_orders = [{"client_order_id": order.client_order_id}]
        recon = v.reconciliation(internal_orders, [])
        assert recon.healthy is True
        assert recon.orders_matched == 1
        assert recon.orders_desynced == 0
