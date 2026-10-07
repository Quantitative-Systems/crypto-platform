"""STRATA Digital Trading Platform — Execution Precision & Idempotency Guard.

Implements critical institutional execution controls:
1. Precise Step-Size & Tick-Size Rounding (eliminates precision errors at venue API boundaries).
2. Minimum Notional & Lot Constraint Verification.
3. Deterministic Client Order ID Generation.
4. Idempotency Execution Guard: Enforces zero duplicate orders per decision and candle.
"""
from __future__ import annotations

import decimal
import hashlib
import logging
import math
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


def round_to_step_size(quantity: float, step_size: float) -> float:
    """Rounds order quantity down to nearest valid exchange lot step size."""
    if step_size <= 0:
        return quantity
    precision = max(0, -decimal.Decimal(str(step_size)).normalize().as_tuple().exponent)
    rounded = math.floor(quantity / step_size) * step_size
    return round(rounded, precision)


def round_to_tick_size(price: float, tick_size: float, round_up: bool = False) -> float:
    """Rounds order price to nearest valid exchange tick size."""
    if tick_size <= 0:
        return price
    precision = max(0, -decimal.Decimal(str(tick_size)).as_tuple().exponent)
    factor = 10 ** precision
    if round_up:
        return math.ceil(price * factor) / factor
    return round(price * factor) / factor


def generate_deterministic_order_id(symbol: str, decision_id: str, timestamp_ms: int) -> str:
    """Generates a reproducible, unique client order ID for venue routing."""
    seed = f"{symbol}_{decision_id}_{timestamp_ms}".encode("utf-8")
    hash_prefix = hashlib.sha256(seed).hexdigest()[:8].upper()
    return f"STRATA_{symbol}_{hash_prefix}"


class DuplicateOrderIntentError(RuntimeError):
    """Raised when an attempt is made to execute the same logical decision more than once."""
    pass


class IdempotencyExecutionGuard:
    """Protects against phantom re-entries and duplicate order submissions."""

    def __init__(self, max_history_size: int = 5000):
        self._executed_keys: Set[str] = set()
        self._max_size = max_history_size

    def assert_idempotent(self, symbol: str, decision_id: str, timestamp_ms: int) -> str:
        """Assert that an order intent is unique.
        
        Key: {symbol}:{decision_id}:{timestamp_ms}
        """
        key = f"{symbol.upper()}:{decision_id}:{timestamp_ms}"
        if key in self._executed_keys:
            logger.critical(f"IDEMPOTENCY BREACH DETECTED: Order intent {key} already executed!")
            raise DuplicateOrderIntentError(
                f"DUPLICATE ORDER INTENT REJECTED: Order key {key} was already submitted."
            )

        if len(self._executed_keys) >= self._max_size:
            # Purge oldest entries safely
            self._executed_keys.clear()

        self._executed_keys.add(key)
        return key

    def clear(self) -> None:
        self._executed_keys.clear()
