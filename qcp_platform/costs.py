"""QCP Platform — single source of truth for trading costs.

The decisive fact of this platform: costs are roughly FIXED in bps (~22bps
roundtrip on a market-in/market-out taker trade) while the natural stop
distance scales with the timeframe. Therefore the cost/stop ratio determines
which horizons are economically tradable *before any signal is considered*.

Measured median ATR in bps of price (from this repo's cache):
    1m  ~3.3     5m ~12.6     15m ~37     1h ~80     4h ~165     1d ~440

So a 2xATR stop is 6.6bps on 1m (costs = 332% of stop => impossible) but
880bps on 1d (costs = 2.5% of stop => fine). Any strategy claiming to scalp
1m profitably with taker fills is claiming to beat arithmetic.

Nothing else in the platform may hard-code a fee. Import from here.
"""
from __future__ import annotations

from dataclasses import dataclass

# Binance USDT-M futures VIP0 baseline (conservative: assume retail, no rebates)
TAKER_BPS = 7.5      # 0.075% market taker
MAKER_BPS = 2.0      # 0.020% limit maker
SLIP_BPS = 3.0       # adverse slippage on market orders (liquid majors)
SPREAD_BPS = 1.0     # quoted spread drag (1bp full spread -> 0.5bp per side)

# Spot-vs-perp basis friction for cash-and-carry (both legs are market orders
# on two different books; we charge an extra explicit basis cost rather than
# pretending spot and perp prices are identical).
BASIS_BPS = 5.0

# A horizon is flagged cost-blocked when a 1R stop is smaller than this multiple
# of roundtrip cost. 3.0x means costs eat a third of the planned risk unit.
MIN_STOP_TO_COST = 3.0


@dataclass(frozen=True)
class CostModel:
    """Per-trade cost in basis points of notional (1bp = 0.01%)."""

    taker_bps: float = TAKER_BPS
    maker_bps: float = MAKER_BPS
    slip_bps: float = SLIP_BPS
    spread_bps: float = SPREAD_BPS
    basis_bps: float = BASIS_BPS

    # ---- single-leg directional (perp) trades -------------------------------
    def entry_bps(self, maker: bool = False) -> float:
        fee = self.maker_bps if maker else self.taker_bps
        slip = 0.0 if maker else self.slip_bps
        return fee + slip + self.spread_bps / 2.0

    def exit_bps(self, maker: bool = False) -> float:
        return self.entry_bps(maker=maker)

    def roundtrip_bps(self, maker_entry: bool = False,
                      maker_exit: bool = False) -> float:
        return self.entry_bps(maker_entry) + self.exit_bps(maker_exit)

    def apply_shock(self, mult: float) -> "CostModel":
        """Stress test: all-in costs scaled by `mult` (gate D5 uses 1.5x)."""
        return CostModel(
            taker_bps=self.taker_bps * mult,
            maker_bps=self.maker_bps * mult,
            slip_bps=self.slip_bps * mult,
            spread_bps=self.spread_bps * mult,
            basis_bps=self.basis_bps * mult,
        )

    # ---- market-neutral carry (spot leg + perp leg, in and out) ------------
    def carry_roundtrip_bps(self) -> float:
        """4 market fills (spot in/out, perp in/out) + basis friction."""
        per_fill = self.taker_bps + self.slip_bps + self.spread_bps / 2.0
        return 4.0 * per_fill + self.basis_bps

    # ---- economics ---------------------------------------------------------
    def cost_to_stop(self, atr_bps: float, atr_mult: float,
                     maker_entry: bool = False) -> float:
        """Ratio of roundtrip cost to the planned stop distance (1R).

        >1.0 means the stop is smaller than the cost of placing the trade:
        the strategy must win more than it can possibly win to break even.
        """
        stop_bps = atr_bps * atr_mult
        if stop_bps <= 0:
            return float("inf")
        return self.roundtrip_bps(maker_entry=maker_entry) / stop_bps

    def is_economic(self, atr_bps: float, atr_mult: float,
                    maker_entry: bool = False) -> bool:
        return self.cost_to_stop(atr_bps, atr_mult, maker_entry) <= 1.0 / MIN_STOP_TO_COST


#: Default model used across the platform (retail taker assumptions).
DEFAULT = CostModel()

#: Median ATR (bps of price) per timeframe, MEASURED from this repo's cache by
#: `runner.measure_median_atr_bps()` (10 assets, full history). Used ONLY for
#: the pre-trade horizon screening table, never for P&L accounting.
MEDIAN_ATR_BPS = {
    "1m": 8.4, "5m": 22.0, "15m": 49.5, "1h": 115.3,
    "4h": 251.8, "1d": 683.4, "1w": 1900.0,
}


def hedge_cost_bps(cost: CostModel | None = None) -> float:
    """Deprecated alias kept for callers that think in 'hedge' terms."""
    return (cost or DEFAULT).carry_roundtrip_bps()
