"""Crypto Trading Platform — Microstructure Paper Matching Simulator.

Simulates realistic order fills against live market prices:
- Accurate bid/ask spread crossing.
- Realistic maker (2 bps) vs taker (6 bps) fee schedules.
- Size-dependent slippage modeling.
- Post-only verification for passive maker limit orders.
"""
from __future__ import annotations

from typing import Optional
import time
import uuid

from crypto_platform.core.domain import (
    ExecutionOrder,
    Fill,
    OrderSide,
    OrderType,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.core.interfaces import IPaperSimulator


class MicrostructurePaperSimulator(IPaperSimulator):
    """Fills orders with realistic spread, slippage, and fee friction."""

    def __init__(
        self,
        maker_fee_bps: float = 2.0,      # 0.02% maker rebate/fee
        taker_fee_bps: float = 6.0,      # 0.06% retail taker fee
        base_slippage_bps: float = 1.5,  # 1.5 bps base slippage
        depth_liquidity_usd: float = 500_000.0,
    ):
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.base_slippage_bps = base_slippage_bps
        self.depth_liquidity_usd = depth_liquidity_usd

    def process_order(
        self, order: ExecutionOrder, current_market: TickerEvent
    ) -> Optional[Fill]:
        """Process an execution order against current market prices."""
        now_ms = int(time.time() * 1000)
        bid = current_market.bid if current_market.bid > 0 else current_market.last_price
        ask = current_market.ask if current_market.ask > 0 else current_market.last_price

        if order.order_type == OrderType.MARKET:
            # Taker fill: Buys cross to Ask, Sells cross to Bid
            base_px = ask if order.side == OrderSide.BUY else bid
            # Size-dependent slippage
            notional = order.quantity * base_px
            slip_mult = 1.0 + (notional / self.depth_liquidity_usd)
            slip_bps = self.base_slippage_bps * slip_mult
            slip_frac = (slip_bps / 10_000.0)

            fill_price = (
                base_px * (1.0 + slip_frac)
                if order.side == OrderSide.BUY
                else base_px * (1.0 - slip_frac)
            )
            is_maker = False
            fee_rate = self.taker_fee_bps / 10_000.0

        elif order.order_type in (OrderType.LIMIT, OrderType.POST_ONLY):
            if order.price is None or order.price <= 0:
                return None

            limit_px = order.price

            # Buy limit fills if ask <= limit (immediate cross) or if market trades through
            if order.side == OrderSide.BUY:
                if order.order_type == OrderType.POST_ONLY and limit_px >= ask:
                    # Post-only rejected because it would cross spread
                    return None
                if limit_px >= ask:
                    fill_price = limit_px
                    is_maker = False
                    fee_rate = self.taker_fee_bps / 10_000.0
                elif current_market.last_price <= limit_px:
                    fill_price = limit_px
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                else:
                    return None  # Unfilled resting limit order

            else:  # SELL
                if order.order_type == OrderType.POST_ONLY and limit_px <= bid:
                    return None
                if limit_px <= bid:
                    fill_price = limit_px
                    is_maker = False
                    fee_rate = self.taker_fee_bps / 10_000.0
                elif current_market.last_price >= limit_px:
                    fill_price = limit_px
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                else:
                    return None

        else:
            return None

        fee_amount = order.quantity * fill_price * fee_rate

        return Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            price=round(fill_price, 4),
            quantity=order.quantity,
            fee=round(fee_amount, 4),
            fee_asset="USDT",
            is_maker=is_maker,
            timestamp_ms=now_ms,
        )
