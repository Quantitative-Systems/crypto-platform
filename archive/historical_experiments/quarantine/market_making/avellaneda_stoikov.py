"""
QCP Phase 11 — Market Making Engine.
Implements the canonical Avellaneda-Stoikov (2008) optimal market-making framework.

Core equations:
1. Reservation (Indifference) Price:
       r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
   where:
       s = mid price
       q = current inventory (contracts)
       gamma = risk aversion parameter
       sigma = asset volatility
       (T - t) = normalized trading horizon remaining

2. Optimal Half-Spreads:
       delta^a + delta^b = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / kappa)
   where:
       kappa = order book liquidity / intensity parameter

3. Microstructure & Adverse Selection Guard:
   Skew quotes when order flow imbalance (OFI) signals toxic informed flow.

PAPER ONLY. No live exchange connectivity.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("QCP.MarketMaking")


@dataclass
class MarketMakingQuotes:
    symbol: str
    mid_price: float
    reservation_price: float
    bid_price: float
    ask_price: float
    bid_quantity: float
    ask_quantity: float
    spread_bps: float
    inventory_q: float
    adverse_selection_warning: bool
    should_cancel_replace: bool
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AvellanedaStoikovModel:
    """
    Optimal high-frequency market making model with inventory risk controls and adverse selection mitigation.
    """

    def __init__(
        self,
        gamma: float = 0.1,        # Risk aversion parameter
        kappa: float = 1.5,        # Order book liquidity parameter
        max_inventory: float = 5.0, # Max net position (e.g. 5 BTC)
        time_horizon_sec: float = 300.0,
        quote_size: float = 0.1,
    ):
        self.gamma = gamma
        self.kappa = kappa
        self.max_inventory = max_inventory
        self.time_horizon_sec = time_horizon_sec
        self.quote_size = quote_size
        self._current_inventory: float = 0.0
        self._last_quotes: Optional[MarketMakingQuotes] = None

    @property
    def inventory(self) -> float:
        return self._current_inventory

    def update_inventory(self, fill_side: str, fill_qty: float) -> None:
        """Updates internal inventory state following a paper fill."""
        if fill_side.upper() in ("BUY", "BID"):
            self._current_inventory += fill_qty
        else:
            self._current_inventory -= fill_qty
        logger.info(f"Market Maker inventory updated: q={self._current_inventory:.4f}")

    def compute_reservation_price(
        self,
        mid_price: float,
        volatility: float,
        time_remaining_sec: float,
    ) -> float:
        """
        r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
        If long inventory (q > 0), reservation price shifts lower to encourage selling.
        If short inventory (q < 0), reservation price shifts higher to encourage buying.
        """
        norm_t = max(0.01, time_remaining_sec / 300.0)
        dollar_vol = mid_price * max(0.001, volatility)
        skew = self._current_inventory * self.gamma * (dollar_vol * 0.05) * norm_t
        return mid_price - skew

    def compute_optimal_spread(
        self,
        volatility: float,
        time_remaining_sec: float,
    ) -> float:
        """
        Computes the total optimal spread:
        s = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / kappa)
        """
        norm_t = max(0.01, time_remaining_sec / 86400.0)
        term1 = self.gamma * (volatility ** 2) * norm_t
        term2 = (2.0 / self.gamma) * math.log(1.0 + (self.gamma / self.kappa))
        return term1 + term2

    def generate_quotes(
        self,
        symbol: str,
        mid_price: float,
        volatility: float = 0.02,
        order_flow_imbalance: float = 0.0,  # -1.0 (heavy sell flow) to +1.0 (heavy buy flow)
        time_remaining_sec: float = 300.0,
    ) -> MarketMakingQuotes:
        """
        Generates two-sided quotes around the reservation price with OFI protection.
        """
        res_price = self.compute_reservation_price(mid_price, volatility, time_remaining_sec)
        opt_spread = self.compute_optimal_spread(volatility, time_remaining_sec)
        half_spread = max(mid_price * 0.0003, opt_spread / 2.0)  # Min spread 3 bps

        # Adverse Selection Guard: if OFI indicates aggressive buyers, skew asks wider and higher
        adverse_selection = abs(order_flow_imbalance) > 0.6
        if order_flow_imbalance > 0.6:
            # Toxic buying: lift ask, pull bid
            ask_price = res_price + half_spread * 1.5
            bid_price = res_price - half_spread * 1.8
        elif order_flow_imbalance < -0.6:
            # Toxic selling: lower bid, pull ask
            bid_price = res_price - half_spread * 1.5
            ask_price = res_price + half_spread * 1.8
        else:
            bid_price = res_price - half_spread
            ask_price = res_price + half_spread

        # Inventory Cap Throttle: don't quote bid if at max inventory, don't quote ask if at min inventory
        bid_qty = self.quote_size if self._current_inventory < self.max_inventory else 0.0
        ask_qty = self.quote_size if self._current_inventory > -self.max_inventory else 0.0

        spread_bps = ((ask_price - bid_price) / mid_price) * 10000.0

        # Cancel-replace threshold (e.g. price drifted > 2 bps from last quote)
        cancel_replace = True
        if self._last_quotes:
            mid_drift = abs(mid_price - self._last_quotes.mid_price) / self._last_quotes.mid_price
            if mid_drift < 0.0002 and not adverse_selection:
                cancel_replace = False

        quotes = MarketMakingQuotes(
            symbol=symbol,
            mid_price=round(mid_price, 2),
            reservation_price=round(res_price, 2),
            bid_price=round(bid_price, 2),
            ask_price=round(ask_price, 2),
            bid_quantity=bid_qty,
            ask_quantity=ask_qty,
            spread_bps=round(spread_bps, 2),
            inventory_q=round(self._current_inventory, 4),
            adverse_selection_warning=adverse_selection,
            should_cancel_replace=cancel_replace,
        )
        self._last_quotes = quotes
        return quotes
