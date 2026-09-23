"""Crypto Trading Platform — foundational plane interfaces.

Ensures strict decoupling:
Strategies -> Portfolio -> Risk Engine -> OMS -> Exchange Adapters.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from .domain import (
    AccountBalance,
    ExecutionOrder,
    Fill,
    OrderIntent,
    OperatingMode,
    Position,
    RiskDecision,
    RiskState,
)
from .events import CandleEvent, OrderBookEvent, TickerEvent


class IStrategy(ABC):
    """Universal Strategy Contract.

    All trading styles (scalping, intraday, swing, positional, investing, carry)
    must implement this interface.
    """
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @property
    @abstractmethod
    def family(self) -> str: ...

    @property
    @abstractmethod
    def horizon(self) -> str: ...

    @property
    @abstractmethod
    def supported_symbols(self) -> List[str]: ...

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None: ...

    @abstractmethod
    def on_candle(self, event: CandleEvent) -> List[OrderIntent]: ...

    @abstractmethod
    def on_order_book(self, event: OrderBookEvent) -> List[OrderIntent]: ...

    @abstractmethod
    def on_fill(self, fill: Fill) -> None: ...


class IRiskEngine(ABC):
    """Independent Fail-Closed Risk Firewall interface."""

    @abstractmethod
    def evaluate_order_intent(
        self,
        intent: OrderIntent,
        current_positions: Dict[str, Position],
        balances: Dict[str, AccountBalance],
        risk_state: RiskState,
        latest_ticker: Optional[TickerEvent] = None,
    ) -> RiskDecision:
        """Evaluate an intent against all 6 risk tiers. Must fail closed."""
        ...

    @abstractmethod
    def update_account_state(self, equity: float, realized_pnl: float) -> None: ...

    @abstractmethod
    def is_kill_switch_active(self, scope: str, target: str) -> bool: ...


class IPortfolioEngine(ABC):
    """Portfolio Construction and Capital Allocation Engine interface."""

    @abstractmethod
    def allocate_capital(
        self,
        intents: List[OrderIntent],
        equity: float,
        active_positions: Dict[str, Position],
    ) -> List[OrderIntent]:
        """Size intents based on volatility targeting and cross-asset correlation."""
        ...


class IOrderManagementSystem(ABC):
    """Order Management System interface."""

    @abstractmethod
    def create_order_from_intent(
        self, intent: OrderIntent, decision: RiskDecision
    ) -> ExecutionOrder: ...

    @abstractmethod
    def update_order_status(
        self, account_id: str, order_id: str, new_status: Any, message: Optional[str] = None
    ) -> None: ...

    @abstractmethod
    def register_fill(self, fill: Fill) -> None: ...

    @abstractmethod
    def get_open_orders(self, account_id: str) -> List[ExecutionOrder]: ...

    @abstractmethod
    def get_positions(self, account_id: str) -> Dict[str, Position]: ...


class IExchangeAdapter(ABC):
    """Universal Venue/Exchange Adapter interface."""

    @property
    @abstractmethod
    def venue_name(self) -> str: ...

    @abstractmethod
    async def connect(self, credentials: Dict[str, str], mode: OperatingMode) -> bool: ...

    @abstractmethod
    async def get_account_balances(self) -> List[AccountBalance]: ...

    @abstractmethod
    async def get_positions(self) -> List[Position]: ...

    @abstractmethod
    async def get_open_orders(self) -> List[ExecutionOrder]: ...

    @abstractmethod
    async def submit_order(self, order: ExecutionOrder) -> ExecutionOrder: ...

    @abstractmethod
    async def cancel_order(self, client_order_id: str, symbol: str) -> bool: ...

    @abstractmethod
    async def verify_permissions(self) -> Dict[str, bool]:
        """Verify API key permissions. If withdrawal is enabled, MUST return False."""
        ...


class IReconciliationEngine(ABC):
    """Continuous State Reconciliation Engine interface."""

    @abstractmethod
    async def reconcile_account(
        self, account_id: str, adapter: IExchangeAdapter, oms: IOrderManagementSystem
    ) -> bool:
        """Compares local ledger vs exchange actuals. Returns True if in sync."""
        ...


class IPaperSimulator(ABC):
    """Forward Paper Trading Microstructure Simulator interface."""

    @abstractmethod
    def process_order(
        self, order: ExecutionOrder, current_market: TickerEvent
    ) -> Optional[Fill]:
        """Simulate realistic fill including slippage, fees, and spread."""
        ...


class ISecurityVault(ABC):
    """Credential Encryption and Secret Vault interface."""

    @abstractmethod
    def encrypt_secret(self, plaintext: str, tenant_id: str) -> str: ...

    @abstractmethod
    def decrypt_secret(self, ciphertext: str, tenant_id: str) -> str: ...
