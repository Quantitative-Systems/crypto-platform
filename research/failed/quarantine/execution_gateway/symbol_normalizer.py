"""
Product 06 — 24/7/365 Live Execution Gateway
Symbol Normalizer Module.
Translates canonical symbols (BTC/USDT, EUR/USD, XAU/USD) to and from broker-specific ticker formats
for Binance, Bybit, OKX, Exness MT5, Vantage MT5, and cTrader.
"""

from typing import Dict, Optional, List
from execution_gateway.contracts.broker_config import BrokerType, BrokerConfig


class SymbolNormalizer:
    """
    Bidirectional symbol translator across crypto exchanges and Forex MT5 brokers.
    """

    DEFAULT_CRYPTO_MAP = {
        "BTC/USDT": "BTCUSDT",
        "ETH/USDT": "ETHUSDT",
        "SOL/USDT": "SOLUSDT",
        "BTC/USD": "BTCUSD",
        "ETH/USD": "ETHUSD",
        "SOL/USD": "SOLUSD",
        "EUR/USD": "EURUSD",
        "GBP/USD": "GBPUSD",
        "XAU/USD": "XAUUSD"
    }

    def __init__(self, config: Optional[BrokerConfig] = None):
        self.config = config or BrokerConfig()
        self._build_maps()

    def _build_maps(self) -> None:
        self.to_broker_map: Dict[str, str] = {}
        self.to_canonical_map: Dict[str, str] = {}

        b_type = self.config.broker_type
        suffix = self.config.symbol_suffix

        for canon, raw in self.DEFAULT_CRYPTO_MAP.items():
            broker_sym = raw
            
            # Broker specific adjustments
            if b_type == BrokerType.EXNESS_MT5:
                # Exness uses BTCUSD, EURUSD, XAUUSD with optional 'm' or suffix
                if "USDT" in raw:
                    broker_sym = raw.replace("USDT", "USD")
                if suffix:
                    broker_sym = f"{broker_sym}{suffix}"
            elif b_type == BrokerType.VANTAGE_MT5:
                if "USDT" in raw:
                    broker_sym = raw.replace("USDT", "USD")
                if suffix:
                    broker_sym = f"{broker_sym}{suffix}"
            elif b_type in [BrokerType.BINANCE, BrokerType.BYBIT, BrokerType.OKX, BrokerType.BITGET]:
                if canon == "BTC/USD":
                    broker_sym = "BTCUSD"
                elif "USDT" in canon:
                    broker_sym = raw

            # Apply custom user override if provided
            if canon in self.config.custom_symbol_mappings:
                broker_sym = self.config.custom_symbol_mappings[canon]

            self.to_broker_map[canon] = broker_sym
            self.to_canonical_map[broker_sym] = canon
            # Also map raw version without slash for convenience
            self.to_canonical_map[raw] = canon

    def to_broker_symbol(self, canonical_symbol: str) -> str:
        """
        Converts canonical format (e.g. 'BTC/USDT' or 'EUR/USD') to broker ticker.
        """
        clean = canonical_symbol.strip()
        if clean in self.to_broker_map:
            return self.to_broker_map[clean]
        
        # Fallback: remove slashes and add suffix
        fallback = clean.replace("/", "") + self.config.symbol_suffix
        return fallback

    def to_canonical_symbol(self, broker_symbol: str) -> str:
        """
        Converts broker ticker (e.g. 'BTCUSDm' or 'BTCUSDT') back to canonical format.
        """
        clean = broker_symbol.strip()
        if clean in self.to_canonical_map:
            return self.to_canonical_map[clean]
        
        # Suffix stripping attempt
        if self.config.symbol_suffix and clean.endswith(self.config.symbol_suffix):
            stripped = clean[:-len(self.config.symbol_suffix)]
            if stripped in self.to_canonical_map:
                return self.to_canonical_map[stripped]

        # Common heuristics
        if clean.endswith("USDT"):
            base = clean[:-4]
            return f"{base}/USDT"
        elif clean.endswith("USD"):
            base = clean[:-3]
            return f"{base}/USD"

        return clean

    def is_symbol_allowed(self, symbol: str) -> bool:
        """
        Checks if symbol is within the authorized tradable whitelist.
        """
        canon = self.to_canonical_symbol(symbol)
        return canon in self.config.allowed_symbols or symbol in self.config.allowed_symbols
