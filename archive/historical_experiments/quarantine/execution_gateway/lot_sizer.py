"""
Product 06 — 24/7/365 Live Execution Gateway
Lot Sizer & Contract Multiplier Normalizer.
Converts risk units to broker lot sizes (0.01 micro-lots to standard lots) across Crypto, Forex, and Metals.
"""

import math
from typing import Tuple, Optional
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType


class LotSizer:
    """
    Calculates exact broker lot sizes and notional exposure for any asset class.
    """

    CONTRACT_SIZES = {
        "BTC/USDT": 1.0,
        "BTC/USD": 1.0,
        "ETH/USDT": 1.0,
        "ETH/USD": 1.0,
        "SOL/USDT": 1.0,
        "SOL/USD": 1.0,
        "EUR/USD": 100000.0,  # 1 standard lot = 100,000 EUR
        "GBP/USD": 100000.0,  # 1 standard lot = 100,000 GBP
        "XAU/USD": 100.0      # 1 standard lot = 100 oz Gold
    }

    def __init__(self, config: Optional[BrokerConfig] = None):
        self.config = config or BrokerConfig()

    def calculate_lots(
        self,
        canonical_symbol: str,
        allocated_units: float,
        entry_price: float,
        account_equity: float
    ) -> Tuple[float, float, float]:
        """
        Converts allocated units to broker lots and validates leverage/margin.
        Returns: (broker_lots, actual_units, notional_usd)
        """
        contract_size = self.CONTRACT_SIZES.get(canonical_symbol, 1.0)
        
        # If Forex/MT5 broker:
        if self.config.broker_type in [
            BrokerType.EXNESS_MT5,
            BrokerType.VANTAGE_MT5,
            BrokerType.PEPPERSTONE_MT5,
            BrokerType.IC_MARKETS_MT5
        ]:
            # Raw lots = allocated units / contract size
            raw_lots = allocated_units / contract_size
            # Round to lot step size (e.g. 0.01)
            step = self.config.lot_step_size
            lots = round(raw_lots / step) * step
            lots = max(self.config.min_lot_size, lots)
            actual_units = lots * contract_size
        else:
            # Standard Crypto exchange (Binance / Bybit / OKX):
            # Units are traded directly in base currency (e.g. 0.001 BTC)
            step = self.config.lot_step_size
            lots = max(self.config.min_lot_size, round(allocated_units / step) * step)
            actual_units = lots

        notional_usd = actual_units * entry_price

        # Max leverage check
        max_notional = account_equity * self.config.max_leverage
        if notional_usd > max_notional and max_notional > 0:
            lots = max(self.config.min_lot_size, (max_notional / entry_price) / contract_size)
            actual_units = lots * contract_size
            notional_usd = actual_units * entry_price

        return round(lots, 4), actual_units, notional_usd
