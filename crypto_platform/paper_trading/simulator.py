"""Crypto Trading Platform — Microstructure Paper Matching Simulator.

Simulates realistic order fills against live market prices:
- Accurate bid/ask spread crossing.
- Realistic maker (2 bps) vs taker (6 bps) fee schedules.
- Size-dependent and latency-dependent slippage modeling.
- Post-only verification for passive maker limit orders.
- Queue clearance probability modeling for resting maker orders.
- Adverse selection drag when market sweeps through resting orders.
- Partial fill simulation for size exceeding immediate top-of-book depth.
"""
from __future__ import annotations

import hashlib
import time
from typing import Optional
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
        depth_liquidity_usd: float = 1_000_000.0,
        maker_queue_clearance_pct: float = 0.50,
        adverse_selection_bps: float = 0.5,
        execution_latency_ms: float = 50.0,
        partial_fill_threshold_pct: float = 0.10,
    ):
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.base_slippage_bps = base_slippage_bps
        self.depth_liquidity_usd = depth_liquidity_usd
        self.maker_queue_clearance_pct = maker_queue_clearance_pct
        self.adverse_selection_bps = adverse_selection_bps
        self.execution_latency_ms = execution_latency_ms
        self.partial_fill_threshold_pct = partial_fill_threshold_pct

    def process_order(
        self, order: ExecutionOrder, current_market: TickerEvent
    ) -> Optional[Fill]:
        """Process an execution order against current market prices."""
        now_ms = int(time.time() * 1000)
        bid = current_market.bid if current_market.bid > 0 else current_market.last_price
        ask = current_market.ask if current_market.ask > 0 else current_market.last_price

        # Check remaining unfilled quantity
        remaining_qty = order.quantity - order.filled_quantity
        if remaining_qty <= 1e-8:
            return None

        if order.order_type == OrderType.MARKET:
            # Taker fill: Buys cross to Ask, Sells cross to Bid
            base_px = ask if order.side == OrderSide.BUY else bid
            # Size-dependent and latency-dependent slippage
            notional = remaining_qty * base_px
            slip_mult = 1.0 + (notional / self.depth_liquidity_usd)
            latency_drift_bps = (self.execution_latency_ms / 100.0) * 0.2
            slip_bps = (self.base_slippage_bps * slip_mult) + latency_drift_bps
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

            if order.side == OrderSide.BUY:
                if limit_px >= ask:
                    if order.order_type == OrderType.POST_ONLY:
                        # Post-only rejected because it crosses the spread
                        return None
                    # Immediate cross as taker
                    fill_price = ask * (1.0 + (self.base_slippage_bps / 10_000.0))
                    is_maker = False
                    fee_rate = self.taker_fee_bps / 10_000.0
                elif current_market.last_price < limit_px:
                    # Traded strictly through limit price -> Guaranteed fill with adverse selection
                    adverse_frac = self.adverse_selection_bps / 10_000.0
                    fill_price = limit_px * (1.0 + adverse_frac)
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                elif current_market.last_price == limit_px:
                    # Touched price: check queue clearance probability
                    q_hash = int(
                        hashlib.md5(f"{order.client_order_id}:{current_market.timestamp_ms}".encode()).hexdigest()[:8],
                        16,
                    ) / 0xFFFFFFFF
                    if q_hash > self.maker_queue_clearance_pct:
                        return None  # Unfilled resting in queue
                    fill_price = limit_px
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                else:
                    return None  # Unfilled resting limit order (market above bid)

            else:  # SELL
                if limit_px <= bid:
                    if order.order_type == OrderType.POST_ONLY:
                        return None
                    fill_price = bid * (1.0 - (self.base_slippage_bps / 10_000.0))
                    is_maker = False
                    fee_rate = self.taker_fee_bps / 10_000.0
                elif current_market.last_price > limit_px:
                    # Traded strictly through limit price -> Guaranteed fill with adverse selection
                    adverse_frac = self.adverse_selection_bps / 10_000.0
                    fill_price = limit_px * (1.0 - adverse_frac)
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                elif current_market.last_price == limit_px:
                    q_hash = int(
                        hashlib.md5(f"{order.client_order_id}:{current_market.timestamp_ms}".encode()).hexdigest()[:8],
                        16,
                    ) / 0xFFFFFFFF
                    if q_hash > self.maker_queue_clearance_pct:
                        return None
                    fill_price = limit_px
                    is_maker = True
                    fee_rate = self.maker_fee_bps / 10_000.0
                else:
                    return None

        else:
            return None

        # Partial fill check if order exceeds threshold of top-level depth
        fill_qty = remaining_qty
        depth_threshold = self.depth_liquidity_usd * self.partial_fill_threshold_pct
        if remaining_qty * fill_price > depth_threshold:
            max_available = depth_threshold / fill_price
            fill_qty = max(round(remaining_qty * 0.5, 4), round(max_available, 4))
            fill_qty = min(remaining_qty, fill_qty)

        fee_amount = fill_qty * fill_price * fee_rate

        return Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            price=round(fill_price, 4),
            quantity=round(fill_qty, 6),
            fee=round(fee_amount, 4),
            fee_asset="USDT",
            is_maker=is_maker,
            timestamp_ms=now_ms,
        )

