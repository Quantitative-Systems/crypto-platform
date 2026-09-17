"""
Product 06 — 24/7/365 Live Execution Gateway
Order Lifecycle & Profit-Lock Stop Synchronizer.
Manages entry routing, exchange-native Stop-Market placement, and dynamic +1.0R ratchet stop updates.
"""

import uuid
import time
from typing import Dict, Optional, List
from portfolio_engine.contracts.portfolio_state import AllocatedTradePlan
from execution_gateway.interfaces.base_gateway import BaseGateway
from execution_gateway.contracts.order_contracts import (
    LiveOrder,
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    PositionRecord,
    ExecutionFill
)


class OrderManager:
    """
    Orchestrates live order lifecycle, native exchange stop placement, and +1.0R profit-lock ratchet adjustments.
    """

    def __init__(
        self,
        gateway: BaseGateway,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75  # Leaves +0.25R locked profit
    ):
        self.gateway = gateway
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r
        self.active_plans: Dict[str, AllocatedTradePlan] = {}
        self.entry_orders: Dict[str, LiveOrder] = {}
        self.stop_orders: Dict[str, LiveOrder] = {}

    async def execute_trade_plan(
        self,
        plan: AllocatedTradePlan,
        use_post_only: bool = True
    ) -> LiveOrder:
        """
        Dispatches initial entry order for an approved AllocatedTradePlan.
        """
        self.active_plans[plan.trade_plan_id] = plan
        is_long = plan.target_price > plan.entry_price
        side = OrderSide.BUY if is_long else OrderSide.SELL
        ord_type = OrderType.POST_ONLY if use_post_only else OrderType.MARKET

        client_id = f"ent_{plan.trade_plan_id[:16]}_{uuid.uuid4().hex[:6]}"
        order = LiveOrder(
            order_id="",
            client_order_id=client_id,
            symbol=plan.symbol,
            side=side,
            order_type=ord_type,
            price=plan.entry_price,
            quantity=plan.allocated_units,
            post_only=use_post_only
        )

        submitted = await self.gateway.submit_order(order)
        self.entry_orders[submitted.order_id] = submitted
        return submitted

    async def on_entry_filled(self, plan: AllocatedTradePlan, fill: ExecutionFill) -> Optional[LiveOrder]:
        """
        Immediately dispatches exchange-native STOP_MARKET order upon entry fill.
        """
        is_long = fill.side == OrderSide.BUY
        sl_side = OrderSide.SELL if is_long else OrderSide.BUY

        sl_client_id = f"sl_{plan.trade_plan_id[:16]}_{uuid.uuid4().hex[:6]}"
        sl_order = LiveOrder(
            order_id="",
            client_order_id=sl_client_id,
            symbol=plan.symbol,
            side=sl_side,
            order_type=OrderType.STOP_MARKET,
            price=0.0,
            quantity=fill.fill_quantity,
            stop_price=plan.stop_loss_price,
            reduce_only=True
        )

        submitted_sl = await self.gateway.submit_order(sl_order)
        self.stop_orders[plan.symbol] = submitted_sl
        return submitted_sl

    async def check_and_update_profit_lock(
        self,
        symbol: str,
        current_price: float,
        high: float,
        low: float
    ) -> Optional[LiveOrder]:
        """
        Checks if active position reached +1.0R MFE and updates native stop order to +0.25R.
        """
        positions = await self.gateway.get_positions()
        if symbol not in positions:
            return None

        pos = positions[symbol]
        if pos.quantity <= 0 or pos.is_profit_locked:
            return None

        # Find matching trade plan
        matching_plan = None
        for plan in self.active_plans.values():
            if plan.symbol == symbol:
                matching_plan = plan
                break

        if not matching_plan:
            return None

        initial_risk_dist = abs(matching_plan.entry_price - matching_plan.stop_loss_price)
        if initial_risk_dist <= 0:
            return None

        # Calculate MFE in R-multiples
        if pos.side == PositionSide.LONG:
            mfe_r = (high - matching_plan.entry_price) / initial_risk_dist
            new_stop_price = matching_plan.entry_price + (initial_risk_dist * (self.lockin_r - self.giveback_r))
        else:
            mfe_r = (matching_plan.entry_price - low) / initial_risk_dist
            new_stop_price = matching_plan.entry_price - (initial_risk_dist * (self.lockin_r - self.giveback_r))

        # Check if +1.0R threshold reached
        if mfe_r >= self.lockin_r:
            # 1. Cancel existing stop order if present
            if symbol in self.stop_orders:
                prev_sl = self.stop_orders[symbol]
                await self.gateway.cancel_order(symbol, prev_sl.order_id)

            # 2. Place new ratcheted stop order
            sl_side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
            new_sl_order = LiveOrder(
                order_id="",
                client_order_id=f"pl_{matching_plan.trade_plan_id[:16]}_{uuid.uuid4().hex[:6]}",
                symbol=symbol,
                side=sl_side,
                order_type=OrderType.STOP_MARKET,
                price=0.0,
                quantity=pos.quantity,
                stop_price=new_stop_price,
                reduce_only=True
            )

            submitted_new_sl = await self.gateway.submit_order(new_sl_order)
            self.stop_orders[symbol] = submitted_new_sl
            pos.is_profit_locked = True
            pos.stop_loss_price = new_stop_price
            return submitted_new_sl

        return None
