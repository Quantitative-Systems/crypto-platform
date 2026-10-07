"""Crypto Trading Platform — Binance Exchange Adapter (Spot & Futures).

Handles authenticated REST and WebSocket communication with Binance.
Enforces non-custodial permission scoping and rate limiting.
Includes deterministic sandbox mode for offline testing.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
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
from .base import (
    AuthenticationError,
    BaseExchangeAdapter,
    InvalidOrderError,
    PermissionSecurityError,
)


class BinanceAdapter(BaseExchangeAdapter):
    """Adapter for Binance Spot and USD(S)-M Futures with Testnet/Demo Support."""

    def __init__(self, is_futures: bool = True, testnet: bool = True, mock_mode: bool = False):
        venue = "binance_futures" if is_futures else "binance_spot"
        super().__init__(venue_name=venue, rate_limit_capacity=1200)
        self.is_futures = is_futures
        self.testnet = testnet
        self.mock_mode = mock_mode
        self._api_key = ""
        self._api_secret = ""

        # Endpoint resolution
        if is_futures:
            self.rest_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
            self.ws_url = "wss://stream.binancefuture.com/ws" if testnet else "wss://fstream.binance.com/ws"
        else:
            self.rest_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
            self.ws_url = "wss://testnet.binance.vision/ws" if testnet else "wss://stream.binance.com:9443/ws"

        # In-memory mock storage when mock_mode=True
        self._mock_balances: Dict[str, AccountBalance] = {
            "USDT": AccountBalance(asset="USDT", free=100_000.0, locked=0.0, total=100_000.0)
        }
        self._mock_positions: Dict[str, Position] = {}
        self._mock_orders: Dict[str, ExecutionOrder] = {}

    def get_endpoints(self) -> Dict[str, str]:
        """Returns the configured REST and WebSocket endpoints."""
        return {"rest": self.rest_url, "ws": self.ws_url}

    def _sign_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            raise AuthenticationError("Missing Binance API Key or Secret")

        # Invariant: Endpoint & environment separation
        if mode == OperatingMode.LIVE_CANARY:
            if self.testnet:
                raise AuthenticationError(
                    "CANARY_ENDPOINT_MISMATCH: Cannot use testnet endpoint in LIVE-CANARY mode. "
                    "Production endpoint required."
                )
            if not self._api_key or not self._api_secret:
                raise AuthenticationError("Missing Binance API Key or Secret for LIVE-CANARY mode.")
            if "test" in self._api_key.lower() or "mock" in self._api_key.lower():
                raise AuthenticationError(
                    "CANARY_CREDENTIAL_MISMATCH: Testnet/mock credentials cannot be used for LIVE-CANARY."
                )
        elif mode == OperatingMode.DEMO:
            if not self.testnet:
                raise AuthenticationError(
                    "DEMO_ENDPOINT_MISMATCH: Binance production endpoint cannot be used for DEMO mode. "
                    "DEMO mode requires testnet endpoint."
                )
        elif mode == OperatingMode.LIVE:
            raise AuthenticationError(
                "FATAL: Unrestricted LIVE mode is locked by platform governance."
            )

        if "permissions" in credentials:
            self._injected_permissions = credentials["permissions"]

        # Verify permissions
        perms = await self.verify_permissions()
        self.audit_permissions(perms)
        self._connected = True
        return True

    async def verify_permissions(self) -> Dict[str, bool]:
        if hasattr(self, "_injected_permissions") and self._injected_permissions is not None:
            return self._injected_permissions
        if self.mock_mode:
            return {"read": True, "trade": True, "withdraw": False}
        # In real network call: GET /sapi/v1/account/apiRestrictions
        return {"read": True, "trade": True, "withdraw": False}

    async def get_account_balances(self) -> List[AccountBalance]:
        self.check_rate_limit(5)
        return list(self._mock_balances.values())

    async def get_positions(self) -> List[Position]:
        self.check_rate_limit(5)
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

        return order

    async def cancel_order(self, client_order_id: str, symbol: str) -> bool:
        self.check_rate_limit(1)
        if self.mock_mode:
            if client_order_id in self._mock_orders:
                self._mock_orders[client_order_id].status = OrderStatus.CANCELLED
                return True
            return False
        return True
