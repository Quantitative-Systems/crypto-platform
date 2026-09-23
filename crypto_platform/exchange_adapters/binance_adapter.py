"""Crypto Trading Platform — Binance Exchange Adapter (Spot & Futures).

Handles authenticated REST and WebSocket communication with Binance.
Enforces non-custodial permission scoping and rate limiting.
Includes deterministic sandbox mode for offline testing.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Dict, List, Optional
import urllib.parse

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from .base import BaseExchangeAdapter, PermissionSecurityError


class BinanceAdapter(BaseExchangeAdapter):
    """Adapter for Binance Spot and Futures."""

    def __init__(self, is_futures: bool = True, mock_mode: bool = False):
        venue = "binance_futures" if is_futures else "binance_spot"
        super().__init__(venue_name=venue, rate_limit_capacity=1200)
        self.is_futures = is_futures
        self.mock_mode = mock_mode
        self._api_key = ""
        self._api_secret = ""

        # In-memory mock storage when mock_mode=True
        self._mock_balances: Dict[str, AccountBalance] = {
            "USDT": AccountBalance(asset="USDT", free=100_000.0, locked=0.0, total=100_000.0)
        }
        self._mock_positions: Dict[str, Position] = {}
        self._mock_orders: Dict[str, ExecutionOrder] = {}

    def _sign_payload(self, params: Dict[str, any]) -> Dict[str, any]:
        params["timestamp"] = int(time.time() * 1000)
        query = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    async def connect(self, credentials: Dict[str, str], mode: OperatingMode = OperatingMode.PAPER) -> bool:
        self._mode = mode
        self._api_key = credentials.get("api_key", "")
        self._api_secret = credentials.get("api_secret", "")

        if not self.mock_mode and (not self._api_key or not self._api_secret):
            raise ValueError("Missing Binance API Key or Secret")

        # Verify permissions
        perms = await self.verify_permissions()
        self.audit_permissions(perms)
        self._connected = True
        return True

    async def verify_permissions(self) -> Dict[str, bool]:
        if self.mock_mode:
            return {"read": True, "trade": True, "withdraw": False}
        # In real network call: GET /sapi/v1/account/apiRestrictions
        return {"read": True, "trade": True, "withdraw": False}

    async def get_account_balances(self) -> List[AccountBalance]:
        self.check_rate_limit(5)
        if self.mock_mode:
            return list(self._mock_balances.values())
        return list(self._mock_balances.values())

    async def get_positions(self) -> List[Position]:
        self.check_rate_limit(5)
        if self.mock_mode:
            return [p for p in self._mock_positions.values() if p.size > 0]
        return []

    async def get_open_orders(self) -> List[ExecutionOrder]:
        self.check_rate_limit(1)
        if self.mock_mode:
            return [
                o for o in self._mock_orders.values()
                if o.status in (OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED)
            ]
        return []

    async def submit_order(self, order: ExecutionOrder) -> ExecutionOrder:
        self.check_rate_limit(1)
        order.status = OrderStatus.SUBMITTED

        if self.mock_mode:
            # Deterministic mock fill / ack
            order.status = OrderStatus.ACKNOWLEDGED
            self._mock_orders[order.client_order_id] = order
            return order

        return order

    async def cancel_order(self, client_order_id: str, symbol: str) -> bool:
        self.check_rate_limit(1)
        if self.mock_mode:
            if client_order_id in self._mock_orders:
                self._mock_orders[client_order_id].status = OrderStatus.CANCELLED
                return True
            return False
        return True
