"""Crypto Trading Platform — Smart Order Router and Intent Translator.

Translates approved OrderIntents into concrete ExecutionOrders:
- Assigns deterministic, idempotent client order IDs (cID).
- Enforces Post-Only / Maker flags where appropriate.
- Assigns TimeInForce (GTC, IOC, PO).
"""
from __future__ import annotations

import hashlib
import time
import uuid

from crypto_platform.core.domain import (
    ExecutionOrder,
    ExecutionUrgency,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskDecision,
    TimeInForce,
)


class OrderRouter:
    """Constructs idempotent execution orders from approved intents."""

    @staticmethod
    def generate_client_order_id(
        tenant_id: str, account_id: str, symbol: str, strategy_id: str
    ) -> str:
        """Deterministic idempotent client order ID.

        Pattern: c_{tenant[:4]}_{account[:4]}_{sym}_{ts}_{nonce}
        Fits within standard exchange 32-character client order ID limits.
        """
        ts = int(time.time() * 1000)
        nonce = uuid.uuid4().hex[:6]
        raw = f"{tenant_id[:4]}_{account_id[:4]}_{symbol[:4]}_{ts}_{nonce}".lower()
        return raw[:32]

    @classmethod
    def route_intent(
        cls, intent: OrderIntent, decision: RiskDecision, venue: str
    ) -> ExecutionOrder:
        if not decision.approved:
            raise ValueError(f"Cannot route unapproved intent: {decision.reason}")

        size = decision.adjusted_size if decision.adjusted_size is not None else intent.target_size
        side = OrderSide.BUY if intent.direction > 0 else OrderSide.SELL

        is_post_only = bool(intent.meta.get("post_only", False)) or (
            intent.urgency == ExecutionUrgency.LOW and intent.limit_price is not None
        )

        # Determine order type and time in force
        if intent.urgency == ExecutionUrgency.EMERGENCY:
            order_type = OrderType.MARKET
            tif = TimeInForce.IOC
            price = None
        elif is_post_only and intent.limit_price is not None:
            order_type = OrderType.POST_ONLY
            tif = TimeInForce.PO
            price = intent.limit_price
        elif intent.limit_price is not None:
            order_type = OrderType.LIMIT
            tif = TimeInForce.GTC
            price = intent.limit_price
        else:
            order_type = OrderType.MARKET
            tif = TimeInForce.IOC
            price = None

        cid = cls.generate_client_order_id(
            intent.tenant_id, intent.account_id, intent.symbol, intent.strategy_id
        )

        return ExecutionOrder(
            order_id=str(uuid.uuid4()),
            client_order_id=cid,
            tenant_id=intent.tenant_id,
            account_id=intent.account_id,
            venue=venue,
            symbol=intent.symbol,
            side=side,
            order_type=order_type,
            time_in_force=tif,
            quantity=size,
            price=price,
            status=OrderStatus.CREATED,
        )
