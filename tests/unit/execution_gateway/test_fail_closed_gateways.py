"""
Unit tests for live gateway Fail-Closed invariant enforcement.
Verifies that CCXTUniversalGateway and MT5ForexGateway fail closed in live mode
and only permit simulation when explicitly requested.
"""

import pytest
import asyncio
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.contracts.order_contracts import LiveOrder, OrderType, OrderSide, OrderStatus
from execution_gateway.gateways.ccxt_universal_gateway import CCXTUniversalGateway
from execution_gateway.gateways.mt5_forex_gateway import MT5ForexGateway


@pytest.mark.anyio
async def test_ccxt_live_gateway_fails_closed_without_credentials():
    """Live CCXT gateway without API credentials must raise RuntimeError and remain not connected."""
    cfg = BrokerConfig(broker_type=BrokerType.BYBIT, is_simulated=False, api_key=None, api_secret=None)
    gateway = CCXTUniversalGateway(cfg)
    
    with pytest.raises(RuntimeError, match="Missing API credentials|CCXT library not installed"):
        await gateway.connect()
        
    assert gateway.is_connected is False


@pytest.mark.anyio
async def test_ccxt_live_gateway_rejects_orders_when_not_connected():
    """Live CCXT gateway must reject order submission when not connected to exchange."""
    cfg = BrokerConfig(broker_type=BrokerType.BYBIT, is_simulated=False)
    gateway = CCXTUniversalGateway(cfg)
    
    order = LiveOrder(
        order_id="test_ord_1",
        client_order_id="c_1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=60000.0,
        quantity=1.0
    )
    
    result = await gateway.submit_order(order)
    assert result.status == OrderStatus.REJECTED


@pytest.mark.anyio
async def test_ccxt_simulation_mode_permitted_when_explicitly_configured():
    """CCXT gateway in explicit simulation mode connects and processes simulated orders."""
    cfg = BrokerConfig(broker_type=BrokerType.BYBIT, is_simulated=True)
    gateway = CCXTUniversalGateway(cfg)
    
    connected = await gateway.connect()
    assert connected is True
    assert gateway.is_connected is True
    
    order = LiveOrder(
        order_id="test_sim_1",
        client_order_id="c_sim_1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=60000.0,
        quantity=1.0
    )
    result = await gateway.submit_order(order)
    assert result.status == OrderStatus.NEW


@pytest.mark.anyio
async def test_mt5_live_gateway_fails_closed_without_credentials():
    """Live MT5 gateway without account credentials must raise RuntimeError and remain not connected."""
    cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, is_simulated=False, account_id=None)
    gateway = MT5ForexGateway(cfg)
    
    with pytest.raises(RuntimeError, match="Missing account_id|MetaTrader5 Python package not installed"):
        await gateway.connect()
        
    assert gateway.is_connected is False


@pytest.mark.anyio
async def test_mt5_live_gateway_rejects_orders_when_not_connected():
    """Live MT5 gateway must reject order submission when not connected to terminal."""
    cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, is_simulated=False)
    gateway = MT5ForexGateway(cfg)
    
    order = LiveOrder(
        order_id="test_mt5_1",
        client_order_id="c_mt5_1",
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=60000.0,
        quantity=1.0
    )
    
    result = await gateway.submit_order(order)
    assert result.status == OrderStatus.REJECTED


@pytest.mark.anyio
async def test_mt5_simulation_mode_permitted_when_explicitly_configured():
    """MT5 gateway in explicit simulation mode connects and processes simulated orders."""
    cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, is_simulated=True)
    gateway = MT5ForexGateway(cfg)
    
    connected = await gateway.connect()
    assert connected is True
    assert gateway.is_connected is True
    
    order = LiveOrder(
        order_id="test_sim_mt5_1",
        client_order_id="c_sim_mt5_1",
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=60000.0,
        quantity=1.0
    )
    result = await gateway.submit_order(order)
    assert result.status == OrderStatus.NEW
