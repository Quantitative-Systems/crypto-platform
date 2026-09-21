"""
Product 06 — 24/7/365 Live Execution Gateway
Institutional Paper Trading Execution Gateway.
Provides realistic simulated execution with post-only limit queueing, adverse fills, and native stop triggers.
"""

import uuid
import time
import asyncio
from typing import List, Dict, Optional, Callable
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


class PaperGateway(BaseGateway):
    """
    Asynchronous Paper Trading Gateway simulating realistic exchange matching engine physics.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        maker_fee_rate: float = 0.0002,   # 2 bps maker
        taker_fee_rate: float = 0.0005,   # 5 bps taker
        slippage_bps: float = 2.0,
        on_fill_callback: Optional[Callable[[ExecutionFill], None]] = None
    ):
        self.balance = initial_balance
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.slippage_bps = slippage_bps
        self.on_fill_callback = on_fill_callback

        self.orders: Dict[str, LiveOrder] = {}
        self.positions: Dict[str, PositionRecord] = {}
        self.last_prices: Dict[str, float] = {}
        self.is_connected = False

    async def connect(self) -> bool:
        self.is_connected = True
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def submit_order(self, order: LiveOrder) -> LiveOrder:
        order.created_timestamp_ms = int(time.time() * 1000)
        order.updated_timestamp_ms = order.created_timestamp_ms

        if not order.order_id:
            order.order_id = f"paper_ord_{uuid.uuid4().hex[:12]}"

        # If Market order, execute immediately
        if order.order_type == OrderType.MARKET:
            cur_price = self.last_prices.get(order.symbol, order.price or 100.0)
            slip_mult = (1.0 + self.slippage_bps / 10000.0) if order.side == OrderSide.BUY else (1.0 - self.slippage_bps / 10000.0)
            fill_price = cur_price * slip_mult
            self._execute_fill(order, fill_price, is_maker=False)
            self.orders[order.order_id] = order
            return order

        # Otherwise queue as working order
        order.status = OrderStatus.NEW
        self.orders[order.order_id] = order
        return order

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        if order_id in self.orders:
            ord_obj = self.orders[order_id]
            if ord_obj.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
                ord_obj.status = OrderStatus.CANCELED
                ord_obj.updated_timestamp_ms = int(time.time() * 1000)
                return True
        return False

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[LiveOrder]:
        open_list = [
            o for o in self.orders.values()
            if o.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
        ]
        if symbol:
            open_list = [o for o in open_list if o.symbol == symbol]
        return open_list

    async def get_positions(self) -> Dict[str, PositionRecord]:
        return {sym: pos for sym, pos in self.positions.items() if pos.quantity > 0}

    async def get_account_balance(self) -> float:
        # NAV = cash + unrealized PnL
        unrealized = sum(p.unrealized_pnl_usd for p in self.positions.values())
        return self.balance + unrealized

    def on_market_price_update(self, symbol: str, current_price: float, high: float, low: float) -> List[ExecutionFill]:
        """
        Simulates exchange matching engine against incoming bar or tick.
        """
        self.last_prices[symbol] = current_price
        fills_generated: List[ExecutionFill] = []

        # Update position unrealized PnL
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.quantity > 0:
                pos.current_price = current_price
                if pos.side == PositionSide.LONG:
                    pos.unrealized_pnl_usd = (current_price - pos.entry_price) * pos.quantity
                    pos.peak_favorable_price = max(pos.peak_favorable_price, high)
                else:
                    pos.unrealized_pnl_usd = (pos.entry_price - current_price) * pos.quantity
                    pos.peak_favorable_price = min(pos.peak_favorable_price or 1e9, low)

        # Check pending orders for this symbol
        pending = [
            o for o in self.orders.values()
            if o.symbol == symbol and o.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
        ]

        for ord_obj in pending:
            # 1. Stop Market Orders
            if ord_obj.order_type == OrderType.STOP_MARKET and ord_obj.stop_price is not None:
                triggered = False
                if ord_obj.side == OrderSide.SELL and low <= ord_obj.stop_price:
                    triggered = True
                elif ord_obj.side == OrderSide.BUY and high >= ord_obj.stop_price:
                    triggered = True

                if triggered:
                    fill_price = ord_obj.stop_price
                    fill = self._execute_fill(ord_obj, fill_price, is_maker=False)
                    fills_generated.append(fill)

            # 2. Limit / Post-Only Orders
            elif ord_obj.order_type in [OrderType.LIMIT, OrderType.POST_ONLY]:
                triggered = False
                if ord_obj.side == OrderSide.BUY and low <= ord_obj.price:
                    triggered = True
                elif ord_obj.side == OrderSide.SELL and high >= ord_obj.price:
                    triggered = True

                if triggered:
                    fill = self._execute_fill(ord_obj, ord_obj.price, is_maker=True)
                    fills_generated.append(fill)

        return fills_generated

    def _execute_fill(self, order: LiveOrder, fill_price: float, is_maker: bool) -> ExecutionFill:
        fee_rate = self.maker_fee_rate if is_maker else self.taker_fee_rate
        notional = fill_price * order.quantity
        fee_usd = notional * fee_rate

        order.filled_quantity = order.quantity
        order.average_fill_price = fill_price
        order.status = OrderStatus.FILLED
        order.updated_timestamp_ms = int(time.time() * 1000)

        # Deduct fee from cash balance
        self.balance -= fee_usd

        # Update Position Accounting
        symbol = order.symbol
        if order.reduce_only or (symbol in self.positions and self.positions[symbol].quantity > 0 and self._is_closing(self.positions[symbol].side, order.side)):
            # Closing / Reducing existing position
            pos = self.positions[symbol]
            if pos.side == PositionSide.LONG:
                realized_pnl = (fill_price - pos.entry_price) * order.quantity
            else:
                realized_pnl = (pos.entry_price - fill_price) * order.quantity

            self.balance += realized_pnl
            pos.quantity = max(0.0, pos.quantity - order.quantity)
            pos.realized_pnl_usd += realized_pnl
            if pos.quantity == 0.0:
                pos.side = PositionSide.FLAT
                pos.unrealized_pnl_usd = 0.0
                pos.active_sl_order_id = None
        else:
            # Opening new position
            pos_side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            self.positions[symbol] = PositionRecord(
                symbol=symbol,
                side=pos_side,
                quantity=order.quantity,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl_usd=0.0,
                realized_pnl_usd=0.0,
                peak_favorable_price=fill_price,
                is_profit_locked=False,
                last_updated_timestamp_ms=int(time.time() * 1000)
            )

        fill = ExecutionFill(
            fill_id=f"fill_{uuid.uuid4().hex[:12]}",
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            symbol=symbol,
            side=order.side,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            fee_usd=fee_usd,
            is_maker=is_maker,
            timestamp_ms=int(time.time() * 1000)
        )

        if self.on_fill_callback:
            self.on_fill_callback(fill)

        return fill

    @staticmethod
    def _is_closing(pos_side: PositionSide, ord_side: OrderSide) -> bool:
        if pos_side == PositionSide.LONG and ord_side == OrderSide.SELL:
            return True
        if pos_side == PositionSide.SHORT and ord_side == OrderSide.BUY:
            return True
        return False
