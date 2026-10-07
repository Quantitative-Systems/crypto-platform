"""Institutional Transaction Cost Model.

Models taker/maker fees, adverse slippage, bid-ask spread drag,
and minimum stop-to-cost economic feasibility.
"""
from __future__ import annotations

from dataclasses import dataclass

# Binance USDT-M futures VIP0 baseline (conservative: retail tier, no rebates)
TAKER_BPS = 7.5      # 0.075% market taker
MAKER_BPS = 2.0      # 0.020% limit maker
SLIP_BPS = 3.0       # adverse slippage on market orders (liquid majors)
SPREAD_BPS = 1.0     # quoted spread drag (1bp full spread -> 0.5bp per side)
BASIS_BPS = 5.0      # basis friction for cash-and-carry / cross-venue

MIN_STOP_TO_COST = 3.0


@dataclass(frozen=True)
class CostModel:
    """Per-trade transaction cost in basis points of notional (1 bp = 0.01%)."""

    taker_bps: float = TAKER_BPS
    maker_bps: float = MAKER_BPS
    slip_bps: float = SLIP_BPS
    spread_bps: float = SPREAD_BPS
    basis_bps: float = BASIS_BPS

    def entry_bps(self, maker: bool = False) -> float:
        fee = self.maker_bps if maker else self.taker_bps
        slip = 0.0 if maker else self.slip_bps
        return fee + slip + self.spread_bps / 2.0

    def exit_bps(self, maker: bool = False) -> float:
        return self.entry_bps(maker=maker)

    def roundtrip_bps(self, maker_entry: bool = False, maker_exit: bool = False) -> float:
        return self.entry_bps(maker_entry) + self.exit_bps(maker_exit)

    def is_tradable_stop(self, stop_distance_bps: float) -> bool:
        """Verify if stop distance is economically viable against roundtrip friction."""
        rt = self.roundtrip_bps()
        return stop_distance_bps >= rt * MIN_STOP_TO_COST
