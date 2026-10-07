"""
QCP Phase 8 — Multi-Venue Connectivity: Canonical Exchange Adapter Base.
Defines the standard exchange-neutral interface required of every venue adapter.

Every adapter must implement:
1. connect()
2. authenticate()
3. market_data()
4. balances()
5. positions()
6. orders()
7. cancel()
8. modify()
9. fills()
10. reconciliation()

INVARIANT: No strategy may depend directly on a single exchange API.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class VenueBalance:
    asset: str
    free: float
    locked: float
    total: float


@dataclass
class VenuePosition:
    symbol: str
    side: str  # LONG / SHORT
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl_usd: float
    liquidation_price: Optional[float] = None
    leverage: float = 1.0


@dataclass
class VenueOrderResponse:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    filled_qty: float
    avg_price: float
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ReconciliationReport:
    venue_id: str
    timestamp_utc: str
    orders_matched: int
    orders_desynced: int
    positions_matched: int
    positions_desynced: int
    balance_drift_usd: float
    discrepancies: List[str]
    healthy: bool


class ExchangeAdapterBase(abc.ABC):
    """
    Abstract Base Class for all QCP Venue Adapters.
    """

    def __init__(self, venue_id: str, is_paper: bool = True):
        self.venue_id = venue_id
        self.is_paper = is_paper
        self._connected = False
        self._authenticated = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @abc.abstractmethod
    def connect(self) -> bool:
        """Establish transport connection to venue."""
        pass

    @abc.abstractmethod
    def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Authenticate session with venue."""
        pass

    @abc.abstractmethod
    def market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch current market snapshot (ticker, top of book)."""
        pass

    @abc.abstractmethod
    def balances(self) -> Dict[str, VenueBalance]:
        """Query account balances."""
        pass

    @abc.abstractmethod
    def positions(self) -> List[VenuePosition]:
        """Query open positions."""
        pass

    @abc.abstractmethod
    def orders(self, symbol: Optional[str] = None) -> List[VenueOrderResponse]:
        """Query active or historical orders."""
        pass

    @abc.abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
    ) -> VenueOrderResponse:
        """Submit a new order to the venue."""
        pass

    @abc.abstractmethod
    def cancel(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancel an open order."""
        pass

    @abc.abstractmethod
    def modify(self, order_id: str, new_price: Optional[float] = None, new_qty: Optional[float] = None) -> VenueOrderResponse:
        """Modify an existing open order."""
        pass

    @abc.abstractmethod
    def fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve historical execution fills."""
        pass

    @abc.abstractmethod
    def reconciliation(self, internal_orders: List[Dict[str, Any]], internal_positions: List[Dict[str, Any]]) -> ReconciliationReport:
        """Reconcile internal platform state against exchange ground truth."""
        pass
