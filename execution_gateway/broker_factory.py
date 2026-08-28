"""
Product 06 — 24/7/365 Live Execution Gateway
Universal Broker Factory.
Instantiates the appropriate exchange/broker gateway based on user configuration.
"""

from typing import Optional
from execution_gateway.interfaces.base_gateway import BaseGateway
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.gateways.paper_gateway import PaperGateway
from execution_gateway.gateways.binance_futures_gateway import BinanceFuturesGateway
from execution_gateway.gateways.ccxt_universal_gateway import CCXTUniversalGateway
from execution_gateway.gateways.mt5_forex_gateway import MT5ForexGateway


class BrokerFactory:
    """
    Factory creating live or paper gateways for any crypto exchange or Forex broker.
    """

    @staticmethod
    def create_gateway(config: Optional[BrokerConfig] = None) -> BaseGateway:
        cfg = config or BrokerConfig()
        b_type = cfg.broker_type

        if b_type == BrokerType.PAPER:
            return PaperGateway(initial_balance=10000.0)

        elif b_type == BrokerType.BINANCE:
            return BinanceFuturesGateway(
                api_key=cfg.api_key or "",
                api_secret=cfg.api_secret or "",
                testnet=cfg.testnet
            )

        elif b_type in [
            BrokerType.EXNESS_MT5,
            BrokerType.VANTAGE_MT5,
            BrokerType.PEPPERSTONE_MT5,
            BrokerType.IC_MARKETS_MT5
        ]:
            return MT5ForexGateway(config=cfg)

        elif b_type in [
            BrokerType.BYBIT,
            BrokerType.OKX,
            BrokerType.BITGET,
            BrokerType.KRAKEN,
            BrokerType.COINBASE,
            BrokerType.CTRADER
        ]:
            return CCXTUniversalGateway(config=cfg)

        # Default fallback
        return PaperGateway(initial_balance=10000.0)
