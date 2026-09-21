"""
Unit tests for SymbolNormalizer.
Tests symbol translation and reversibility across Binance, Bybit, Exness MT5, and Vantage MT5.
"""

from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.symbol_normalizer import SymbolNormalizer


def test_symbol_normalizer_binance():
    cfg = BrokerConfig(broker_type=BrokerType.BINANCE)
    sn = SymbolNormalizer(cfg)
    
    assert sn.to_broker_symbol("BTC/USDT") == "BTCUSDT"
    assert sn.to_broker_symbol("ETH/USDT") == "ETHUSDT"
    assert sn.to_canonical_symbol("BTCUSDT") == "BTC/USDT"
    assert sn.is_symbol_allowed("BTC/USDT") is True
    assert sn.is_symbol_allowed("DOGE/USDT") is False


def test_symbol_normalizer_exness_mt5():
    cfg = BrokerConfig(
        broker_type=BrokerType.EXNESS_MT5,
        symbol_suffix="m",
        allowed_symbols=["BTC/USD", "EUR/USD", "XAU/USD"]
    )
    sn = SymbolNormalizer(cfg)
    
    assert sn.to_broker_symbol("BTC/USD") == "BTCUSDm"
    assert sn.to_broker_symbol("EUR/USD") == "EURUSDm"
    assert sn.to_broker_symbol("XAU/USD") == "XAUUSDm"
    assert sn.to_canonical_symbol("BTCUSDm") == "BTC/USD"
    assert sn.to_canonical_symbol("EURUSDm") == "EUR/USD"
    assert sn.is_symbol_allowed("BTC/USD") is True


def test_symbol_normalizer_vantage_mt5():
    cfg = BrokerConfig(
        broker_type=BrokerType.VANTAGE_MT5,
        symbol_suffix="+",
        allowed_symbols=["BTC/USD", "EUR/USD"]
    )
    sn = SymbolNormalizer(cfg)
    
    assert sn.to_broker_symbol("BTC/USD") == "BTCUSD+"
    assert sn.to_broker_symbol("EUR/USD") == "EURUSD+"
    assert sn.to_canonical_symbol("BTCUSD+") == "BTC/USD"
