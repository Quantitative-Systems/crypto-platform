"""Crypto Trading Platform — Order Management System (OMS).

Maintains the internal ground-truth ledger of working orders, positions, and fills.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import time

from crypto_platform.core.domain import (
    ExecutionOrder,
    Fill,
    OrderIntent,
    OrderSide,
    OrderStatus,
    Position,
    RiskDecision,
)
from crypto_platform.core.interfaces import IOrderManagementSystem
from .router import OrderRouter
from .state_machine import OrderStateMachine


class OrderManagementSystem(IOrderManagementSystem):
    """Central OMS tracking orders, fills, and positions per account."""

    def __init__(self):
        # account_id -> {order_id: ExecutionOrder}
        self._orders: Dict[str, Dict[str, ExecutionOrder]] = {}
        # account_id -> {client_order_id: order_id}
        self._cid_map: Dict[str, Dict[str, str]] = {}
        # account_id -> {symbol: Position}
        self._positions: Dict[str, Dict[str, Position]] = {}
        # order_id -> List[Fill]
        self._fills: Dict[str, List[Fill]] = {}

    def create_order_from_intent(
        self, intent: OrderIntent, decision: RiskDecision, venue: str = "binance"
    ) -> ExecutionOrder:
        order = OrderRouter.route_intent(intent, decision, venue=venue)
        OrderStateMachine.transition(order, OrderStatus.RISK_CHECKED)

        acct_orders = self._orders.setdefault(intent.account_id, {})
        acct_orders[order.order_id] = order
        acct_cids = self._cid_map.setdefault(intent.account_id, {})
        acct_cids[order.client_order_id] = order.order_id

        return order

    def update_order_status(
        self, account_id: str, order_id: str, new_status: OrderStatus, message: Optional[str] = None
    ) -> None:
        acct_orders = self._orders.get(account_id, {})
        order = acct_orders.get(order_id)
        if order is None:
            raise KeyError(f"Order {order_id} not found for account {account_id}")

        OrderStateMachine.transition(order, new_status, reason=message or "")
        order.updated_at_ms = int(time.time() * 1000)

    def register_fill(self, fill: Fill, account_id: str) -> None:
        """Process a fill, update order status and update position."""
        acct_orders = self._orders.get(account_id, {})
        order = acct_orders.get(fill.order_id)
        if order:
            order.filled_quantity += fill.quantity
            order.updated_at_ms = int(time.time() * 1000)
            if order.status == OrderStatus.RISK_CHECKED:
                OrderStateMachine.transition(order, OrderStatus.SUBMITTED)
            if order.filled_quantity >= order.quantity - 1e-8:
                if OrderStateMachine.can_transition(order.status, OrderStatus.FILLED):
                    OrderStateMachine.transition(order, OrderStatus.FILLED)
            else:
                if OrderStateMachine.can_transition(order.status, OrderStatus.PARTIALLY_FILLED):
                    OrderStateMachine.transition(order, OrderStatus.PARTIALLY_FILLED)

        # Record fill
        self._fills.setdefault(fill.order_id, []).append(fill)

        # Update position
        acct_positions = self._positions.setdefault(account_id, {})
        pos = acct_positions.get(fill.symbol)
        fill_dir = 1 if fill.side == OrderSide.BUY else -1

        if pos is None or pos.size == 0:
            # Opening new position
            acct_positions[fill.symbol] = Position(
                symbol=fill.symbol,
                direction=fill_dir,
                size=fill.quantity,
                entry_price=fill.price,
                mark_price=fill.price,
                updated_at_ms=fill.timestamp_ms,
            )
        elif pos.direction == fill_dir:
            # Adding to existing position
            new_size = pos.size + fill.quantity
            weighted_entry = (pos.size * pos.entry_price + fill.quantity * fill.price) / new_size
            pos.size = new_size
            pos.entry_price = weighted_entry
            pos.mark_price = fill.price
            pos.updated_at_ms = fill.timestamp_ms
        else:
            # Reducing or flipping position
            if fill.quantity <= pos.size:
                # Partial or full close
                closed_size = fill.quantity
                pnl = (fill.price - pos.entry_price) * closed_size * pos.direction
                pos.realized_pnl += pnl
                pos.size -= closed_size
                pos.mark_price = fill.price
                pos.updated_at_ms = fill.timestamp_ms
                if pos.size <= 1e-8:
                    pos.size = 0.0
                    pos.direction = 0
            else:
                # Closed and flipped
                closed_size = pos.size
                pnl = (fill.price - pos.entry_price) * closed_size * pos.direction
                pos.realized_pnl += pnl
                remaining = fill.quantity - closed_size
                pos.size = remaining
                pos.direction = fill_dir
                pos.entry_price = fill.price
                pos.mark_price = fill.price
                pos.updated_at_ms = fill.timestamp_ms

    def get_open_orders(self, account_id: str) -> List[ExecutionOrder]:
        acct_orders = self._orders.get(account_id, {})
        return [
            o for o in acct_orders.values()
            if o.status in (OrderStatus.CREATED, OrderStatus.RISK_CHECKED, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED)
        ]

    def get_positions(self, account_id: str) -> Dict[str, Position]:
        return {
            sym: pos for sym, pos in self._positions.get(account_id, {}).items()
            if pos.size > 0
        }
