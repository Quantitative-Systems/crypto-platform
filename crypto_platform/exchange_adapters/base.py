"""Crypto Trading Platform — Universal Base Exchange Adapter.

Provides common foundation for all broker and exchange connectors:
- Rate limiting via token-bucket algorithm.
- Scoped permission auditing (enforcing withdrawal-disabled non-custodial rule).
- Unified exception hierarchy.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Dict, List, Optional
import time

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    Position,
)
from crypto_platform.core.interfaces import IExchangeAdapter


class ExchangeAdapterError(Exception):
    """Base exception for all exchange and broker adapter errors."""
    pass


class PermissionSecurityError(ExchangeAdapterError):
    """Raised when an API key carries dangerous or prohibited permissions (e.g. Withdraw)."""
    pass


class AuthenticationError(ExchangeAdapterError):
    """Raised when broker/exchange authentication fails."""
    pass


class NetworkConnectivityError(ExchangeAdapterError):
    """Raised on connection timeout, disconnect, or network transport failure."""
    pass


class RateLimitExceededError(ExchangeAdapterError):
    """Raised when local or remote exchange rate limits are exceeded."""
    pass


class InvalidOrderError(ExchangeAdapterError):
    """Raised when an order fails broker/exchange validation (e.g. tick size, min notional)."""
    pass


class InsufficientMarginError(ExchangeAdapterError):
    """Raised when an account lacks sufficient margin or balance to place an order."""
    pass


class OrderNotFoundError(ExchangeAdapterError):
    """Raised when querying, cancelling, or modifying an order that does not exist."""
    pass


class TokenBucketRateLimiter:
    """Token-bucket algorithm for preventing exchange HTTP 429 rate limit bans."""

    def __init__(self, capacity: int = 1200, refill_rate_per_sec: float = 20.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.tokens = float(capacity)
        self.last_refill_ts = time.time()

    def acquire(self, tokens_needed: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill_ts
        self.last_refill_ts = now
        self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        return False


class BaseExchangeAdapter(IExchangeAdapter):
    """Abstract base adapter with rate limiting and security audits."""

    def __init__(self, venue_name: str, rate_limit_capacity: int = 1200):
        self._venue_name = venue_name
        self._rate_limiter = TokenBucketRateLimiter(capacity=rate_limit_capacity)
        self._mode = OperatingMode.PAPER
        self._connected = False

    @property
    def venue_name(self) -> str:
        return self._venue_name

    def audit_permissions(self, permissions: Dict[str, bool]) -> None:
        """Enforce strict non-custodial invariant: WITHDRAWAL IS FORBIDDEN."""
        prohibited = ["withdraw", "transfer", "withdrawal", "internal_transfer"]
        for p in prohibited:
            if permissions.get(p, False):
                raise PermissionSecurityError(
                    f"CRITICAL SECURITY VIOLATION: API key for {self._venue_name} has '{p}' "
                    f"permission enabled. Non-custodial platform policy rejects any credential "
                    f"with withdrawal capabilities."
                )

    def check_rate_limit(self, weight: int = 1) -> None:
        if not self._rate_limiter.acquire(weight):
            raise RateLimitExceededError(f"Local rate limit budget exceeded on {self._venue_name}")
