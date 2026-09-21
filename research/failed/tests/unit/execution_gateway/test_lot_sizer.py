"""
Unit tests for LotSizer.
Tests 0.01 micro-lot calculations across Forex, Gold, and Crypto on micro accounts.
"""

from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.lot_sizer import LotSizer


def test_lot_sizer_forex_micro_account():
    cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, min_lot_size=0.01, lot_step_size=0.01)
    ls = LotSizer(cfg)
    
    # On a $10 account with 1000 units EUR/USD @ 1.0800
    lots, actual_units, notional = ls.calculate_lots(
        canonical_symbol="EUR/USD",
        allocated_units=1000.0,  # 0.01 lot
        entry_price=1.0800,
        account_equity=10.0
    )
    
    assert lots == 0.01
    assert actual_units == 1000.0
    assert abs(notional - 1080.0) < 1.0


def test_lot_sizer_gold_micro_lots():
    cfg = BrokerConfig(broker_type=BrokerType.VANTAGE_MT5, min_lot_size=0.01)
    ls = LotSizer(cfg)
    
    # 0.01 lot Gold = 1 oz
    lots, actual_units, notional = ls.calculate_lots(
        canonical_symbol="XAU/USD",
        allocated_units=1.0,
        entry_price=2600.0,
        account_equity=100.0
    )
    
    assert lots == 0.01
    assert actual_units == 1.0
    assert abs(notional - 2600.0) < 1.0


def test_lot_sizer_crypto():
    cfg = BrokerConfig(broker_type=BrokerType.BINANCE, min_lot_size=0.001, lot_step_size=0.001)
    ls = LotSizer(cfg)
    
    lots, actual_units, notional = ls.calculate_lots(
        canonical_symbol="BTC/USDT",
        allocated_units=0.05,
        entry_price=60000.0,
        account_equity=1000.0
    )
    
    assert lots == 0.05
    assert actual_units == 0.05
    assert notional == 3000.0
