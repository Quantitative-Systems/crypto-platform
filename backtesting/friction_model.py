"""
Product 01: Crypto Platform - Institutional Trading Friction Engine
Simulates Binance VIP-0 taker fees, execution slippage, and bid-ask spread drag.
"""

from dataclasses import dataclass


@dataclass
class FrictionModel:
    taker_fee_pct: float = 0.00075  # 0.075% Binance Taker Fee
    slippage_pct: float = 0.00030   # 0.03% Market Slippage
    spread_pct: float = 0.00010     # 0.01% Bid-Ask Spread Drag

    def calculate_buy_fill(self, raw_price: float) -> float:
        """Calculates actual higher fill price for BUY market order due to slippage + spread."""
        return raw_price * (1.0 + self.slippage_pct + (self.spread_pct / 2.0))

    def calculate_sell_fill(self, raw_price: float) -> float:
        """Calculates actual lower fill price for SELL market order due to slippage + spread."""
        return raw_price * (1.0 - self.slippage_pct - (self.spread_pct / 2.0))

    def calculate_fee(self, notional_value_usd: float) -> float:
        """Calculates transaction fee for position entry/exit in USD."""
        return notional_value_usd * self.taker_fee_pct