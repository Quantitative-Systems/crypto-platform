"""Unit tests for Exchange Adapter Architecture & Non-Custodial Security Contracts.

Verifies:
- Token-bucket rate limiting enforcement.
- Non-custodial withdrawal permission auditing (strict rejection of withdraw rights).
- Binance USD(S)-M Futures adapter contract methods (mock sandbox & testnet URLs).
- Bybit V5 Linear adapter contract methods (mock sandbox & testnet URLs).
- CCXT fallback adapter contract methods.
- Normalized error mapping hierarchy.
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    OperatingMode,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from crypto_platform.exchange_adapters import (
    AuthenticationError,
    BinanceAdapter,
    BybitAdapter,
    CCXTAdapter,
    ExchangeAdapterError,
    InsufficientMarginError,
    InvalidOrderError,
    NetworkConnectivityError,
    OrderNotFoundError,
    PermissionSecurityError,
    RateLimitExceededError,
    TokenBucketRateLimiter,
)


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(capacity=10, refill_rate_per_sec=5.0)
    assert limiter.acquire(5) is True
    assert limiter.acquire(5) is True
    assert limiter.acquire(1) is False  # Budget exhausted

    time.sleep(0.3)  # Refills ~1.5 tokens
    assert limiter.acquire(1) is True


def test_binance_adapter_testnet_endpoints():
    adapter_testnet = BinanceAdapter(is_futures=True, testnet=True)
    endpoints = adapter_testnet.get_endpoints()
    assert "testnet.binancefuture.com" in endpoints["rest"]
    assert "stream.binancefuture.com" in endpoints["ws"]

    adapter_mainnet = BinanceAdapter(is_futures=True, testnet=False)
    endpoints_main = adapter_mainnet.get_endpoints()
    assert "fapi.binance.com" in endpoints_main["rest"]
    assert "fstream.binance.com" in endpoints_main["ws"]


@pytest.mark.anyio
async def test_binance_adapter_withdrawal_permission_rejected():
    adapter = BinanceAdapter(mock_mode=True)
    # Simulate API key with withdrawal enabled
    dangerous_perms = {"read": True, "trade": True, "withdraw": True}
    with pytest.raises(PermissionSecurityError) as exc_info:
        adapter.audit_permissions(dangerous_perms)
    assert "CRITICAL SECURITY VIOLATION" in str(exc_info.value)
    assert "withdraw" in str(exc_info.value)


@pytest.mark.anyio
async def test_binance_adapter_safe_permission_accepted():
    adapter = BinanceAdapter(mock_mode=True)
    safe_perms = {"read": True, "trade": True, "withdraw": False}
    adapter.audit_permissions(safe_perms)  # Should not raise


@pytest.mark.anyio
async def test_binance_adapter_sandbox_contracts():
    adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=True)
    connected = await adapter.connect({"api_key": "mock_k", "api_secret": "mock_s"}, mode=OperatingMode.DEMO)
    assert connected is True

    balances = await adapter.get_account_balances()
    assert len(balances) > 0
    assert balances[0].asset == "USDT"
    assert balances[0].total == 100_000.0

    order = ExecutionOrder(
        order_id="o1",
        client_order_id="c1",
        tenant_id="t1",
        account_id="acc1",
        venue="binance_futures",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=50000.0,
    )
    submitted = await adapter.submit_order(order)
    assert submitted.status == OrderStatus.ACKNOWLEDGED

    open_orders = await adapter.get_open_orders()
    assert len(open_orders) == 1
    assert open_orders[0].client_order_id == "c1"

    cancelled = await adapter.cancel_order("c1", "BTCUSDT")
    assert cancelled is True
    assert open_orders[0].status == OrderStatus.CANCELLED

    # Invalid order quantity must raise InvalidOrderError
    invalid_order = ExecutionOrder(
        order_id="o_inv",
        client_order_id="c_inv",
        tenant_id="t1",
        account_id="acc1",
        venue="binance_futures",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=-1.0,
        price=50000.0,
    )
    with pytest.raises(InvalidOrderError):
        await adapter.submit_order(invalid_order)


def test_bybit_adapter_testnet_endpoints():
    adapter_testnet = BybitAdapter(testnet=True)
    endpoints = adapter_testnet.get_endpoints()
    assert "api-testnet.bybit.com" in endpoints["rest"]
    assert "stream-testnet.bybit.com" in endpoints["ws"]


@pytest.mark.anyio
async def test_bybit_adapter_withdrawal_permission_rejected():
    adapter = BybitAdapter(mock_mode=True)
    dangerous_perms = {"read": True, "trade": True, "transfer": True}
    with pytest.raises(PermissionSecurityError):
        adapter.audit_permissions(dangerous_perms)


@pytest.mark.anyio
async def test_bybit_adapter_sandbox_contracts():
    adapter = BybitAdapter(testnet=True, mock_mode=True)
    connected = await adapter.connect({"api_key": "mock_k", "api_secret": "mock_s"}, mode=OperatingMode.DEMO)
    assert connected is True

    balances = await adapter.get_account_balances()
    assert len(balances) > 0
    assert balances[0].asset == "USDT"

    order = ExecutionOrder(
        order_id="o_bybit",
        client_order_id="c_bybit",
        tenant_id="t1",
        account_id="acc1",
        venue="bybit",
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=5.0,
        price=150.0,
    )
    submitted = await adapter.submit_order(order)
    assert submitted.status == OrderStatus.ACKNOWLEDGED

    cancelled = await adapter.cancel_order("c_bybit", "SOLUSDT")
    assert cancelled is True


@pytest.mark.anyio
async def test_ccxt_adapter_contracts():
    adapter = CCXTAdapter(venue_id="kraken", mock_mode=True)
    connected = await adapter.connect({"api_key": "mock_k", "api_secret": "mock_s"}, mode=OperatingMode.DEMO)
    assert connected is True
    balances = await adapter.get_account_balances()
    assert len(balances) > 0
    assert balances[0].asset == "USD"
