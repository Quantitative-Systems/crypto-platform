"""Tests for Broker & Exchange Adapters and Non-Custodial Security Gates."""
import pytest
from crypto_platform.core.domain import ExecutionOrder, OrderSide, OrderStatus, OrderType, TimeInForce
from crypto_platform.exchange_adapters.base import (
    BaseExchangeAdapter,
    PermissionSecurityError,
    TokenBucketRateLimiter,
)
from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
from crypto_platform.exchange_adapters.bybit_adapter import BybitAdapter
from crypto_platform.exchange_adapters.ccxt_adapter import CCXTAdapter


def test_non_custodial_withdrawal_security_audit():
    adapter = BinanceAdapter(mock_mode=True)
    # Dangerous key with withdrawal capability
    dangerous_perms = {"read": True, "trade": True, "withdraw": True}
    with pytest.raises(PermissionSecurityError, match="CRITICAL SECURITY VIOLATION"):
        adapter.audit_permissions(dangerous_perms)


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate_per_sec=1.0)
    # Drain capacity
    assert limiter.acquire(3) is True
    assert limiter.acquire(2) is True
    # Bucket now empty
    assert limiter.acquire(1) is False


@pytest.mark.anyio
async def test_binance_adapter_mock_lifecycle():
    adapter = BinanceAdapter(mock_mode=True)
    connected = await adapter.connect({"api_key": "mock_k", "api_secret": "mock_s"})
    assert connected is True

    balances = await adapter.get_account_balances()
    assert len(balances) > 0
    assert balances[0].asset == "USDT"

    order = ExecutionOrder(
        order_id="o_test",
        client_order_id="c_test",
        tenant_id="t1",
        account_id="a1",
        venue="binance_futures",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=60_000.0,
    )
    res = await adapter.submit_order(order)
    assert res.status == OrderStatus.ACKNOWLEDGED

    cancelled = await adapter.cancel_order("c_test", "BTCUSDT")
    assert cancelled is True


@pytest.mark.anyio
async def test_bybit_adapter_mock_lifecycle():
    adapter = BybitAdapter(mock_mode=True)
    connected = await adapter.connect({"api_key": "k", "api_secret": "s"})
    assert connected is True
    balances = await adapter.get_account_balances()
    assert len(balances) > 0


@pytest.mark.anyio
async def test_ccxt_adapter_mock_lifecycle():
    adapter = CCXTAdapter(venue_id="kraken", mock_mode=True)
    connected = await adapter.connect({"api_key": "k", "api_secret": "s"})
    assert connected is True
    balances = await adapter.get_account_balances()
    assert balances[0].asset == "USD"
