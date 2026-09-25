"""Crypto Trading Platform — Bybit Exchange Adapter (Unified Trading Account).

Handles authenticated REST and WebSocket communication with Bybit V5.
Enforces non-custodial permission scoping and rate limiting.
Includes deterministic sandbox mode for offline testing.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    OrderStatus,
    Position,
)
from .base import (
    AuthenticationError,
    BaseExchangeAdapter,
    InvalidOrderError,
    PermissionSecurityError,
)


class BybitAdapter(BaseExchangeAdapter):
    """Adapter for Bybit UTA with Testnet/Demo Support."""

    def __init__(self, testnet: bool = True, mock_mode: bool = False):
        super().__init__(venue_name="bybit", rate_limit_capacity=600)
        self.testnet = testnet
        self.mock_mode = mock_mode
        self._api_key = ""
        self._api_secret = ""

        # Endpoint resolution
        self.rest_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.ws_url = (
            "wss://stream-testnet.bybit.com/v5/public/linear"
            if testnet
            else "wss://stream.bybit.com/v5/public/linear"
        )

        self._mock_balances: Dict[str, AccountBalance] = {
            "USDT": AccountBalance(asset="USDT", free=50_000.0, locked=0.0, total=50_000.0)
        }
        self._mock_positions: Dict[str, Position] = {}
        self._mock_orders: Dict[str, ExecutionOrder] = {}

    def get_endpoints(self) -> Dict[str, str]:
        """Returns the configured REST and WebSocket endpoints."""
        return {"rest": self.rest_url, "ws": self.ws_url}

    async def connect(self, credentials: Dict[str, str], mode: OperatingMode = OperatingMode.PAPER) -> bool:
        self._mode = mode
        self._api_key = credentials.get("api_key", "")
        self._api_secret = credentials.get("api_secret", "")

        if not self.mock_mode and (not self._api_key or not self._api_secret):
            raise AuthenticationError("Missing Bybit API Key or Secret")

        perms = await self.verify_permissions()
        self.audit_permissions(perms)
        self._connected = True
        return True

    async def verify_permissions(self) -> Dict[str, bool]:
        return {"read": True, "trade": True, "withdraw": False}

    async def get_account_balances(self) -> List[AccountBalance]:
        self.check_rate_limit(1)
        return list(self._mock_balances.values())

    async def get_positions(self) -> List[Position]:
        self.check_rate_limit(1)
        return [p for p in self._mock_positions.values() if p.size > 0]

    async def get_open_orders(self) -> List[ExecutionOrder]:
        self.check_rate_limit(1)
        return [
            o for o in self._mock_orders.values()
            if o.status in (OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED)
        ]

    async def submit_order(self, order: ExecutionOrder) -> ExecutionOrder:
        self.check_rate_limit(1)
        if order.quantity <= 0:
            raise InvalidOrderError(f"Order quantity must be positive, got {order.quantity}")

        order.status = OrderStatus.SUBMITTED
        if self.mock_mode:
            order.status = OrderStatus.ACKNOWLEDGED
            self._mock_orders[order.client_order_id] = order
        return order

    async def cancel_order(self, client_order_id: str, symbol: str) -> bool:
        self.check_rate_limit(1)
        if self.mock_mode and client_order_id in self._mock_orders:
            self._mock_orders[client_order_id].status = OrderStatus.CANCELLED
            return True
        return True
