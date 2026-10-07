"""Unit tests for STRATA Multi-Broker Adapter Framework."""
import pytest
from execution.adapters.broker_adapters import (
    BinanceBrokerAdapter,
    BrokerVenueType,
    BybitBrokerAdapter,
    MetaTrader5BrokerAdapter,
)
from execution.adapters.execution_adapters import OrderIntent


@pytest.mark.asyncio
async def test_binance_broker_adapter_lifecycle():
    adapter = BinanceBrokerAdapter(is_testnet=True)
    connected = await adapter.connect()
    assert connected
    assert adapter.is_connected
    assert adapter.venue_type == BrokerVenueType.BINANCE

    caps = adapter.get_capabilities()
    assert caps.supports_market_orders
    assert caps.supports_hedge_mode
    assert caps.supports_testnet

    balances = await adapter.get_account_balances()
    assert len(balances) >= 1
    assert balances[0].asset == "USDT"

    # In testnet (paper/demo), place_order produces simulated fill
    intent = OrderIntent(
        intent_id="INT_TEST_BNB",
        decision_id="DEC_BNB",
        symbol="BTCUSDT",
        direction=1,
        entry_price=65000.0,
        initial_stop_price=64000.0,
        target_price=69000.0,
        planned_r=4.0,
        risk_usd=1000.0,
        size_units=0.5,
        created_at_ts=1700000000000,
    )
    res = await adapter.place_order(intent)
    assert res["status"] == "NEW"
    assert res["venue"] == "BINANCE"

    await adapter.disconnect()
    assert not adapter.is_connected


@pytest.mark.asyncio
async def test_bybit_and_mt5_adapters():
    bybit = BybitBrokerAdapter(is_testnet=True)
    await bybit.connect()
    assert bybit.is_connected
    assert bybit.get_capabilities().max_leverage == 10.0
    await bybit.disconnect()

    mt5 = MetaTrader5BrokerAdapter(is_testnet=True)
    await mt5.connect()
    assert mt5.is_connected
    assert mt5.get_capabilities().venue_type == BrokerVenueType.METATRADER5
    await mt5.disconnect()
