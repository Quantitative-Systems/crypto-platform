"""Crypto Trading Platform — Order Lifecycle State Machine.

Strictly manages state transitions:
CREATED -> RISK_CHECKED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED
Terminating states: FILLED, CANCELLED, REJECTED, EXPIRED, FAILED.
Critical state: UNKNOWN (requires immediate reconciliation; never assume failed).
"""
from __future__ import annotations

from typing import Dict, Set
from crypto_platform.core.domain import ExecutionOrder, OrderStatus


# Valid state transitions
VALID_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.RISK_CHECKED, OrderStatus.REJECTED, OrderStatus.FAILED},
    OrderStatus.RISK_CHECKED: {OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.FAILED, OrderStatus.CANCELLED},
    OrderStatus.SUBMITTED: {OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.FAILED, OrderStatus.UNKNOWN},
    OrderStatus.ACKNOWLEDGED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.UNKNOWN},
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.UNKNOWN},
    OrderStatus.UNKNOWN: {OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED},
    # Terminating states (no further transitions)
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.FAILED: set(),
}


class OrderStateMachine:
    """Enforces valid order lifecycle transitions."""

    @staticmethod
    def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
        return target in VALID_TRANSITIONS.get(current, set())

    @staticmethod
    def transition(order: ExecutionOrder, target: OrderStatus, reason: str = "") -> None:
        if not OrderStateMachine.can_transition(order.status, target):
            raise ValueError(
                f"Illegal order transition for {order.client_order_id}: "
                f"{order.status.value} -> {target.value}"
            )
        order.status = target
        if reason and target in (OrderStatus.REJECTED, OrderStatus.FAILED):
            order.rejection_reason = reason
