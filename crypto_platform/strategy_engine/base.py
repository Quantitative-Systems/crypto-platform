"""Crypto Trading Platform — Base Strategy Contract.

Standard foundation for all strategy plugin families.
Strategies consume market events and emit OrderIntents.
They NEVER place orders directly on exchanges.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional
import time
import uuid

from crypto_platform.core.domain import ExecutionUrgency, Fill, OrderIntent
from crypto_platform.core.events import CandleEvent, OrderBookEvent
from crypto_platform.core.interfaces import IStrategy


class BaseStrategy(IStrategy):
    """Base implementation providing state management and intent generation helpers."""

    def __init__(
        self,
        strategy_id: str,
        family: str,
        horizon: str,
        supported_symbols: List[str],
        tenant_id: str = "t_default",
        account_id: str = "acct_default",
    ):
        self._strategy_id = strategy_id
        self._family = family
        self._horizon = horizon
        self._supported_symbols = list(supported_symbols)
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.config: Dict[str, Any] = {}
        self.recent_candles: Dict[str, List[CandleEvent]] = {}
        self.active_positions: Dict[str, float] = {}

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def family(self) -> str:
        return self._family

    @property
    def horizon(self) -> str:
        return self._horizon

    @property
    def supported_symbols(self) -> List[str]:
        return self._supported_symbols

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = dict(config)

    def create_intent(
        self,
        symbol: str,
        direction: int,
        target_size: float,
        urgency: ExecutionUrgency = ExecutionUrgency.NORMAL,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        target_price: Optional[float] = None,
        reason: str = "",
    ) -> OrderIntent:
        """Helper to create an OrderIntent."""
        return OrderIntent(
            intent_id=str(uuid.uuid4()),
            strategy_id=self.strategy_id,
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            symbol=symbol,
            direction=direction,
            target_size=target_size,
            urgency=urgency,
            limit_price=limit_price,
            stop_price=stop_price,
            target_price=target_price,
            horizon=self.horizon,
            created_at_ms=int(time.time() * 1000),
            signal_reason=reason,
        )

    def on_order_book(self, event: OrderBookEvent) -> List[OrderIntent]:
        return []

    def on_fill(self, fill: Fill) -> None:
        # Update local tracking of position size
        current = self.active_positions.get(fill.symbol, 0.0)
        dir_mult = 1.0 if fill.side.value == "BUY" else -1.0
        self.active_positions[fill.symbol] = current + fill.quantity * dir_mult
