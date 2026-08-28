"""
Unit tests for BrokerFactory.
Tests dynamic creation of Paper, Binance, Exness MT5, Vantage MT5, and Bybit CCXT gateways.
"""

from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.broker_factory import BrokerFactory
from execution_gateway.gateways.paper_gateway import PaperGateway
from execution_gateway.gateways.binance_futures_gateway import BinanceFuturesGateway
from execution_gateway.gateways.mt5_forex_gateway import MT5ForexGateway
from execution_gateway.gateways.ccxt_universal_gateway import CCXTUniversalGateway


def test_broker_factory_instantiations():
    # 1. Paper
    g1 = BrokerFactory.create_gateway(BrokerConfig(broker_type=BrokerType.PAPER))
    assert isinstance(g1, PaperGateway)
    
    # 2. Binance
    g2 = BrokerFactory.create_gateway(BrokerConfig(broker_type=BrokerType.BINANCE))
    assert isinstance(g2, BinanceFuturesGateway)
    
    # 3. Exness MT5
    g3 = BrokerFactory.create_gateway(BrokerConfig(broker_type=BrokerType.EXNESS_MT5))
    assert isinstance(g3, MT5ForexGateway)
    
    # 4. Vantage MT5
    g4 = BrokerFactory.create_gateway(BrokerConfig(broker_type=BrokerType.VANTAGE_MT5))
    assert isinstance(g4, MT5ForexGateway)
    
    # 5. Bybit CCXT
    g5 = BrokerFactory.create_gateway(BrokerConfig(broker_type=BrokerType.BYBIT))
    assert isinstance(g5, CCXTUniversalGateway)
