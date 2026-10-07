"""
Product 06 — 24/7/365 Live Execution Gateway
Universal Broker & Multi-Asset (Crypto + Forex) Configuration Contracts.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


class BrokerType(Enum):
    PAPER = "PAPER"
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"
    BITGET = "BITGET"
    KRAKEN = "KRAKEN"
    COINBASE = "COINBASE"
    EXNESS_MT5 = "EXNESS_MT5"
    VANTAGE_MT5 = "VANTAGE_MT5"
    PEPPERSTONE_MT5 = "PEPPERSTONE_MT5"
    IC_MARKETS_MT5 = "IC_MARKETS_MT5"
    CTRADER = "CTRADER"


@dataclass
class BrokerConfig:
    """
    Configuration parameters for connecting to any crypto exchange or Forex broker.
    """
    broker_type: BrokerType = BrokerType.PAPER
    is_simulated: bool = False                # Explicit simulation flag (must be explicitly enabled for non-paper brokers)
    account_id: Optional[str] = None          # MT5 login or exchange Subaccount
    api_key: Optional[str] = None             # Exchange API key
    api_secret: Optional[str] = None          # Exchange API secret / MT5 password
    api_passphrase: Optional[str] = None      # OKX / KuCoin / Bitget passphrase
    server_name: Optional[str] = None         # MT5 broker server (e.g. Exness-Real7, Vantage-Live)
    testnet: bool = False
    
    # Asset Filter: Only trade symbols in this whitelist
    allowed_symbols: List[str] = field(default_factory=lambda: [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BTC/USD", "ETH/USD", "EUR/USD", "XAU/USD"
    ])
    
    # Custom Symbol Suffixes (e.g. '.m' for Exness mini, '+' for Vantage)
    symbol_suffix: str = ""
    custom_symbol_mappings: Dict[str, str] = field(default_factory=dict)
    
    # Lot Sizing & Fractional Controls
    min_lot_size: float = 0.01                # 0.01 micro-lot support
    lot_step_size: float = 0.01
    max_leverage: float = 100.0               # Max broker leverage allowed
    use_post_only: bool = True                # Use post-only maker orders where supported
