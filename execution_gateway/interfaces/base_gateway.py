"""
Product 06 — 24/7/365 Live Execution Gateway
Abstract Base Gateway Interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable
from execution_gateway.contracts.order_contracts import LiveOrder, PositionRecord, ExecutionFill


class BaseGateway(ABC):
    """
    Abstract interface for exchange execution connectivity.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Initializes REST and WebSocket connections to exchange."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes all connections cleanly."""
        pass

    @abstractmethod
    async def submit_order(self, order: LiveOrder) -> LiveOrder:
        """Submits an order to the exchange."""
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancels an existing active order."""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[LiveOrder]:
        """Fetches current working open orders."""
        pass

    @abstractmethod
    async def get_positions(self) -> Dict[str, PositionRecord]:
        """Fetches active open positions across symbols."""
        pass

    @abstractmethod
    async def get_account_balance(self) -> float:
        """Fetches live account total balance / NAV in USDT."""
        pass
