"""Trading Constraints and Sizing Limits for Instruments.

Encapsulates venue-enforced and risk-enforced order parameters:
- Tick size (minimum price increment)
- Step size / lot size (minimum quantity increment)
- Min/Max order notional
- Price/Qty decimal precision
- Market type (SPOT, PERPETUAL_LINEAR, PERPETUAL_INVERSE)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class InstrumentMarketType(str, Enum):
    """Execution instrument structure."""
    SPOT = "SPOT"
    PERPETUAL_LINEAR = "PERPETUAL_LINEAR"       # Margined/settled in quote (e.g., USDT)
    PERPETUAL_INVERSE = "PERPETUAL_INVERSE"     # Margined/settled in base (e.g., BTC coin-margin)
    FUTURES_EXPIRING = "FUTURES_EXPIRING"


@dataclass(frozen=True)
class TradingConstraints:
    """Venue constraints on order parameters."""
    min_order_qty: float = 0.0001
    max_order_qty: float = 100.0
    step_size: float = 0.0001
    min_notional_usd: float = 10.0
    tick_size: float = 0.01
    price_precision: int = 2
    qty_precision: int = 4
    max_leverage: float = 1.0
    market_type: InstrumentMarketType = InstrumentMarketType.SPOT

    def round_price(self, price: float) -> float:
        """Round price to the nearest allowable tick size."""
        if self.tick_size <= 0:
            return round(price, self.price_precision)
        steps = round(price / self.tick_size)
        rounded = steps * self.tick_size
        return round(rounded, self.price_precision)

    def round_qty(self, qty: float) -> float:
        """Round quantity down to the nearest allowable step size."""
        if self.step_size <= 0:
            return round(qty, self.qty_precision)
        steps = math.floor(qty / self.step_size)
        rounded = steps * self.step_size
        return round(rounded, self.qty_precision)

    def validate_order(self, price: float, qty: float, ref_price_usd: float = 1.0) -> tuple[bool, str]:
        """Validate if order conforms to venue constraints."""
        rounded_qty = self.round_qty(qty)
        if rounded_qty < self.min_order_qty:
            return False, f"Order qty {qty} (rounded {rounded_qty}) below min {self.min_order_qty}"
        if rounded_qty > self.max_order_qty:
            return False, f"Order qty {qty} above max {self.max_order_qty}"

        notional_usd = price * rounded_qty * ref_price_usd
        if notional_usd < self.min_notional_usd:
            return False, f"Notional USD {notional_usd:.2f} below min {self.min_notional_usd}"

        return True, "VALID"
