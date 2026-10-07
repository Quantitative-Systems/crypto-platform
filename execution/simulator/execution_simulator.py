"""Institutional Execution Simulator.

Simulates the full microstructure lifecycle between signal generation and exchange fill:
- Signal-to-exchange network latency (50 - 250ms with jitter)
- Exchange order acceptance and queue placement
- Bid-ask spread crossing
- Non-linear orderbook slippage and market impact
- Partial fills on large clip sizes
- Rejection conditions (insufficient margin, rate limit, stale price, disconnect)
- Trading fee deductions (maker vs taker bps)
"""
from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from instrument.instrument_contract import CryptoBaseInstrument
from instrument.trading_constraints import TradingConstraints


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"


class OrderStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class SimulatedOrder:
    """Order parameters submitted to the execution simulator."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    submitted_at: float = field(default_factory=time.time)
    client_tag: str = "SHADOW_ENGINE"


@dataclass(frozen=True)
class ExecutionFill:
    """Execution fill execution details."""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    fill_price: float
    fill_qty: float
    slippage_bps: float
    spread_cost_bps: float
    fee_usd: float
    latency_ms: float
    filled_at: float


@dataclass
class ExecutionResult:
    """Final outcome of an order execution attempt."""
    order_id: str
    status: OrderStatus
    requested_qty: float
    filled_qty: float
    average_fill_price: float
    total_fee_usd: float
    total_slippage_bps: float
    latency_ms: float
    rejection_reason: Optional[str] = None
    fills: List[ExecutionFill] = field(default_factory=list)


class ExecutionSimulator:
    """Microstructure simulation engine for shadow and paper validation."""

    def __init__(
        self,
        base_latency_ms: float = 65.0,
        latency_jitter_ms: float = 20.0,
        taker_fee_bps: float = 4.0,       # 0.04% taker fee
        maker_fee_bps: float = 2.0,       # 0.02% maker fee
        slippage_coeff: float = 0.5,      # Slippage elasticity
        rejection_rate: float = 0.0,      # For adversarial stress tests
        simulate_partial_fills: bool = True,
        random_seed: Optional[int] = 42,
    ):
        self.base_latency_ms = base_latency_ms
        self.latency_jitter_ms = latency_jitter_ms
        self.taker_fee_bps = taker_fee_bps
        self.maker_fee_bps = maker_fee_bps
        self.slippage_coeff = slippage_coeff
        self.rejection_rate = rejection_rate
        self.simulate_partial_fills = simulate_partial_fills
        self._rng = random.Random(random_seed)

    def simulate_latency(self) -> float:
        """Sample realistic round-trip latency in milliseconds."""
        jitter = self._rng.uniform(-self.latency_jitter_ms, self.latency_jitter_ms)
        return max(15.0, self.base_latency_ms + jitter)

    def execute_market_order(
        self,
        order: SimulatedOrder,
        reference_price: float,
        instrument: Optional[CryptoBaseInstrument] = None,
        observed_spread_bps: float = 3.0,
        top_depth_usd: float = 500_000.0,
        force_disconnect: bool = False,
    ) -> ExecutionResult:
        """Execute a market order through realistic microstructure modeling."""
        latency = self.simulate_latency()

        # 1. Exchange disconnect check
        if force_disconnect:
            return ExecutionResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                requested_qty=order.quantity,
                filled_qty=0.0,
                average_fill_price=0.0,
                total_fee_usd=0.0,
                total_slippage_bps=0.0,
                latency_ms=latency,
                rejection_reason="EXCHANGE_DISCONNECTED_OR_GATEWAY_TIMEOUT",
            )

        # 2. Random adversarial rejection check
        if self.rejection_rate > 0.0 and self._rng.random() < self.rejection_rate:
            return ExecutionResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                requested_qty=order.quantity,
                filled_qty=0.0,
                average_fill_price=0.0,
                total_fee_usd=0.0,
                total_slippage_bps=0.0,
                latency_ms=latency,
                rejection_reason="EXCHANGE_REJECT_INSUFFICIENT_LIQUIDITY_OR_BURST",
            )

        # 3. Constraint validation
        constraints = instrument.trading_constraints if instrument else TradingConstraints()
        valid, msg = constraints.validate_order(reference_price, order.quantity)
        if not valid:
            return ExecutionResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                requested_qty=order.quantity,
                filled_qty=0.0,
                average_fill_price=0.0,
                total_fee_usd=0.0,
                total_slippage_bps=0.0,
                latency_ms=latency,
                rejection_reason=f"CONSTRAINT_VIOLATION: {msg}",
            )

        # 4. Spread crossing cost
        half_spread_pct = (observed_spread_bps / 20000.0)

        # 5. Non-linear market impact / slippage calculation
        order_notional_usd = reference_price * order.quantity
        depth_ratio = order_notional_usd / max(1000.0, top_depth_usd)
        slippage_bps = max(0.5, self.slippage_coeff * math.sqrt(depth_ratio) * 10.0 + self._rng.uniform(0.1, 1.0))
        slippage_pct = slippage_bps / 10000.0

        # Effective execution price
        if order.side == OrderSide.BUY:
            fill_price = reference_price * (1.0 + half_spread_pct + slippage_pct)
        else:
            fill_price = reference_price * (1.0 - half_spread_pct - slippage_pct)

        fill_price = constraints.round_price(fill_price)

        # 6. Sizing and partial fill evaluation
        filled_qty = constraints.round_qty(order.quantity)
        is_partial = False
        if self.simulate_partial_fills and order_notional_usd > top_depth_usd * 0.8:
            # Sizing exceeds 80% of top depth -> partial fill
            filled_qty = constraints.round_qty(order.quantity * self._rng.uniform(0.60, 0.85))
            is_partial = True

        notional_filled_usd = fill_price * filled_qty
        fee_usd = notional_filled_usd * (self.taker_fee_bps / 10000.0)

        fill = ExecutionFill(
            fill_id=f"FILL-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            fill_price=fill_price,
            fill_qty=filled_qty,
            slippage_bps=round(slippage_bps, 2),
            spread_cost_bps=observed_spread_bps / 2.0,
            fee_usd=round(fee_usd, 4),
            latency_ms=round(latency, 2),
            filled_at=time.time(),
        )

        status = OrderStatus.PARTIALLY_FILLED if is_partial else OrderStatus.FILLED
        return ExecutionResult(
            order_id=order.order_id,
            status=status,
            requested_qty=order.quantity,
            filled_qty=filled_qty,
            average_fill_price=fill_price,
            total_fee_usd=round(fee_usd, 4),
            total_slippage_bps=round(slippage_bps, 2),
            latency_ms=round(latency, 2),
            rejection_reason=None,
            fills=[fill],
        )
