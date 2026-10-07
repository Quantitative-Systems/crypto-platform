"""
Product 01: Crypto Platform - Institutional Trading Friction Engine
Simulates Binance VIP-0 taker fees, execution slippage, and bid-ask spread drag.

Phase D fill models
-------------------
Three canonical execution hypotheses are tested in Phase D.  Each model changes
only the entry-fill price; all downstream geometry (risk_per_unit, planned R:R,
TP distance) is recomputed causally from that fill inside the backtester.

FILL_MODEL_TAKER         – current default (market order, worst-case fill)
FILL_MODEL_MAKER_TOUCH   – passive limit at the bar open; reduced slippage,
                           maker fee, no adverse spread component
FILL_MODEL_MAKER_CONSERVATIVE – passive limit placed one tick above/below open;
                                zero slippage, maker fee, still pays spread drag
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Canonical fill-model labels (used as keys in reports, never as magic ints)
# ---------------------------------------------------------------------------
FILL_MODEL_TAKER = "TAKER"
FILL_MODEL_MAKER_TOUCH = "MAKER_TOUCH"
FILL_MODEL_MAKER_CONSERVATIVE = "MAKER_CONSERVATIVE"


@dataclass
class FrictionModel:
    taker_fee_pct: float = 0.00075   # 0.075% Binance Taker Fee
    maker_fee_pct: float = 0.00020   # 0.020% Binance Maker Fee
    slippage_pct: float = 0.00030    # 0.03%  Market Slippage (taker only)
    spread_pct: float = 0.00010      # 0.01%  Bid-Ask Spread Drag
    fill_model: str = FILL_MODEL_TAKER  # active fill model label

    # ------------------------------------------------------------------
    # Factory constructors for the three Phase D execution hypotheses
    # ------------------------------------------------------------------
    @classmethod
    def taker(cls) -> "FrictionModel":
        """Market order: full slippage + spread + taker fee."""
        return cls(fill_model=FILL_MODEL_TAKER)

    @classmethod
    def maker_touch(cls) -> "FrictionModel":
        """Passive limit at bar open: half slippage, half spread, maker fee."""
        return cls(
            slippage_pct=0.00015,  # 0.015% — passive touch, some adverse selection
            spread_pct=0.00010,
            taker_fee_pct=0.00075,  # exit is still a market order (taker)
            maker_fee_pct=0.00020,
            fill_model=FILL_MODEL_MAKER_TOUCH,
        )

    @classmethod
    def maker_conservative(cls) -> "FrictionModel":
        """Passive limit one tick inside spread: zero slippage, pays spread, maker fee."""
        return cls(
            slippage_pct=0.0,       # limit fills at or better than open
            spread_pct=0.00010,
            taker_fee_pct=0.00075,  # exit still taker
            maker_fee_pct=0.00020,
            fill_model=FILL_MODEL_MAKER_CONSERVATIVE,
        )

    # ------------------------------------------------------------------
    # Fill-price calculation (accounts for active fill_model)
    # ------------------------------------------------------------------
    def _entry_slippage(self) -> float:
        """Returns entry-side slippage for the active fill model."""
        if self.fill_model == FILL_MODEL_TAKER:
            return self.slippage_pct
        if self.fill_model == FILL_MODEL_MAKER_TOUCH:
            return self.slippage_pct  # already set to 0.015%
        # MAKER_CONSERVATIVE
        return 0.0

    def _entry_fee(self) -> float:
        """Returns per-unit entry fee fraction for the active fill model."""
        if self.fill_model == FILL_MODEL_TAKER:
            return self.taker_fee_pct
        return self.maker_fee_pct  # maker entry

    def _exit_fee(self) -> float:
        """Exit is always a market order (taker) for Phase D hypothesis."""
        return self.taker_fee_pct

    def calculate_buy_fill(self, raw_price: float) -> float:
        """Actual higher fill price for BUY entry (slippage + spread).
        NOTE: does not include fee — fees are accounted for separately in _fee_r.
        """
        return raw_price * (1.0 + self._entry_slippage() + (self.spread_pct / 2.0))

    def calculate_sell_fill(self, raw_price: float) -> float:
        """Actual lower fill price for SELL entry (slippage + spread)."""
        return raw_price * (1.0 - self._entry_slippage() - (self.spread_pct / 2.0))

    def calculate_fee(self, notional_value_usd: float) -> float:
        """Entry transaction fee in USD (uses active fill-model entry fee rate)."""
        return notional_value_usd * self._entry_fee()

    def roundtrip_fee_pct(self) -> float:
        """Total round-trip fee fraction: entry + exit."""
        return self._entry_fee() + self._exit_fee()