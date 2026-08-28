"""
Unit tests for Product 06 — Live Execution Gateway.
Tests PaperGateway and OrderManager post-only execution, native stop placement, and +1.0R profit-lock ratchet.
"""

import pytest
import asyncio
from execution_gateway.contracts.order_contracts import (
    LiveOrder,
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    ExecutionFill
)
from execution_gateway.gateways.paper_gateway import PaperGateway
from execution_gateway.order_manager import OrderManager
from portfolio_engine.contracts.portfolio_state import AllocatedTradePlan


def test_paper_gateway_limit_and_stop_fills():
    async def _run():
        gateway = PaperGateway(initial_balance=10000.0)
        await gateway.connect()
        
        # 1. Place POST_ONLY Limit Buy at $100.0
        buy_ord = LiveOrder(
            order_id="ord_1",
            client_order_id="c_1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.POST_ONLY,
            price=100.0,
            quantity=1.0,
            post_only=True
        )
        await gateway.submit_order(buy_ord)
        assert buy_ord.status == OrderStatus.NEW
        
        # Tick 1: Price is 105.0 -> No Fill
        fills = gateway.on_market_price_update("BTCUSDT", current_price=105.0, high=106.0, low=104.0)
        assert len(fills) == 0
        assert buy_ord.status == OrderStatus.NEW
        
        # Tick 2: Low drops to 99.0 -> Limit Buy Fills
        fills = gateway.on_market_price_update("BTCUSDT", current_price=100.0, high=102.0, low=99.0)
        assert len(fills) == 1
        assert buy_ord.status == OrderStatus.FILLED
        assert fills[0].fill_price == 100.0
        assert fills[0].is_maker is True
        
        # Check Position
        positions = await gateway.get_positions()
        assert "BTCUSDT" in positions
        assert positions["BTCUSDT"].quantity == 1.0
        assert positions["BTCUSDT"].side == PositionSide.LONG

    asyncio.run(_run())


def test_order_manager_profit_lock_ratchet():
    async def _run():
        gateway = PaperGateway(initial_balance=10000.0)
        await gateway.connect()
        om = OrderManager(gateway=gateway, lockin_r=1.0, giveback_r=0.75)
        
        plan = AllocatedTradePlan(
            trade_plan_id="plan_pl_1",
            hypothesis_id="UNIFIED_STRATEGY",
            symbol="BTCUSDT",
            entry_price=100.0,
            stop_loss_price=95.0,  # 1.0R = 5.0
            target_price=125.0,
            allocated_units=1.0,
            allocated_dollar_risk=5.0,
            risk_fraction=0.01,
            volatility_scale_factor=1.0,
            drawdown_dampener_factor=1.0,
            is_approved=True
        )
        
        # 1. Execute Entry
        entry_ord = await om.execute_trade_plan(plan, use_post_only=False)
        # Trigger fill
        fills = gateway.on_market_price_update("BTCUSDT", current_price=100.0, high=100.5, low=99.5)
        
        # Positions should now exist
        pos = (await gateway.get_positions())["BTCUSDT"]
        assert pos.quantity == 1.0
        
        # 2. Attach initial native Stop Loss
        dummy_fill = ExecutionFill(
            fill_id="f1", order_id="ord_e1", client_order_id="c1", symbol="BTCUSDT",
            side=OrderSide.BUY, fill_price=100.0, fill_quantity=1.0, fee_usd=0.05, is_maker=False, timestamp_ms=1000
        )
        sl_order = await om.on_entry_filled(plan, dummy_fill)
        assert sl_order.stop_price == 95.0
        
        # 3. Price rallies to 105.0 (+1.0R MFE)
        ratchet_ord = await om.check_and_update_profit_lock("BTCUSDT", current_price=105.0, high=105.2, low=104.0)
        assert ratchet_ord is not None
        # Stop should be ratcheted to entry + 0.25R = 100.0 + 1.25 = 101.25
        assert ratchet_ord.stop_price == 101.25
        assert pos.is_profit_locked is True

    asyncio.run(_run())
