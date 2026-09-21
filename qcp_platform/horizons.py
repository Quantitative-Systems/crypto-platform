"""QCP Platform — the all-horizon ladder.

One platform, six books, each with its own clock, cost floor, risk budget and
capacity. Capital is allocated by measured out-of-sample performance, not by
preference, and a book that cannot pay its costs is switched off and reported.

The cost floor is the gate that keeps this honest: `min_stop_bps` requires the
planned 1R stop to be at least MIN_STOP_TO_COST x roundtrip cost. SET_5/SET_6
(scalp) fail that test with taker fills on today's data, so they are only
permitted in maker mode and are reported as NOT_ECONOMIC otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .costs import DEFAULT, CostModel


@dataclass(frozen=True)
class Horizon:
    key: str
    label: str
    htf: str                # context clock
    mtf: str                # intermediate clock
    ltf: str                # execution clock
    style: str
    max_hold_bars: int      # on the LTF clock
    atr_mult: float         # stop distance in ATR(ltf)
    target_r: float         # take profit in R
    fixed_risk_pct: float   # per-trade risk when this book trades alone
    capital_weight: float   # share of platform risk budget
    maker_entry: bool
    min_stop_bps: float
    families: tuple = field(default=())


HORIZONS: dict[str, Horizon] = {
    "SCALP": Horizon(
        key="SCALP", label="Scalping", htf="15m", mtf="5m", ltf="1m",
        style="seconds-minutes", max_hold_bars=60, atr_mult=2.0, target_r=1.5,
        fixed_risk_pct=0.0015, capital_weight=0.05, maker_entry=True,
        min_stop_bps=60.0, families=("scalp_micro",)),
    "INTRADAY": Horizon(
        key="INTRADAY", label="Intraday", htf="4h", mtf="1h", ltf="15m",
        style="hours", max_hold_bars=48, atr_mult=2.0, target_r=2.0,
        fixed_risk_pct=0.0025, capital_weight=0.15, maker_entry=True,
        min_stop_bps=45.0, families=("mean_revert", "grid_range", "trend_breakout")),
    "SWING": Horizon(
        key="SWING", label="Swing", htf="1d", mtf="4h", ltf="1h",
        style="days", max_hold_bars=72, atr_mult=2.5, target_r=2.5,
        fixed_risk_pct=0.0035, capital_weight=0.25, maker_entry=False,
        min_stop_bps=60.0, families=("trend_breakout", "trend_rider",
                                     "mean_revert", "pairs_statarb")),
    "POSITION": Horizon(
        key="POSITION", label="Position", htf="1w", mtf="1d", ltf="4h",
        style="weeks-months", max_hold_bars=90, atr_mult=3.0, target_r=3.0,
        fixed_risk_pct=0.0040, capital_weight=0.25, maker_entry=False,
        min_stop_bps=80.0, families=("trend_breakout", "trend_rider",
                                     "xs_momentum")),
    "INVEST": Horizon(
        key="INVEST", label="Investing", htf="1M", mtf="1w", ltf="1d",
        style="months-years", max_hold_bars=250, atr_mult=4.0, target_r=4.0,
        fixed_risk_pct=0.0050, capital_weight=0.20, maker_entry=False,
        min_stop_bps=100.0, families=("invest_dca", "xs_momentum",
                                      "trend_rider")),
    "CARRY": Horizon(
        key="CARRY", label="Funding carry (market-neutral)", htf="1d", mtf="1d",
        ltf="1d", style="weeks-months", max_hold_bars=90, atr_mult=0.0,
        target_r=0.0, fixed_risk_pct=0.0030, capital_weight=0.10,
        maker_entry=False, min_stop_bps=0.0, families=("funding_carry",)),
}

HORIZON_ORDER = ("SCALP", "INTRADAY", "SWING", "POSITION", "INVEST", "CARRY")


def economic_screen(cost: CostModel | None = None,
                    atr_bps: dict | None = None) -> list:
    """Pre-trade truth table: can each horizon pay its own costs?

    Uses measured median ATR per timeframe (screening only, never P&L).
    """
    from .costs import MEDIAN_ATR_BPS
    cost = cost or DEFAULT
    atr_bps = atr_bps or MEDIAN_ATR_BPS
    rows = []
    for key in HORIZON_ORDER:
        h = HORIZONS[key]
        if h.atr_mult <= 0:
            rows.append(dict(horizon=key, style=h.style, stop_bps=None,
                             cost_bps=round(cost.carry_roundtrip_bps(), 1),
                             cost_to_stop=None, economic=None,
                             note="market-neutral carry: costs vs funding yield"))
            continue
        a = atr_bps.get(h.ltf, 0.0)
        r = cost.cost_to_stop(a, h.atr_mult, maker_entry=h.maker_entry)
        rows.append(dict(horizon=key, style=h.style,
                         stop_bps=round(a * h.atr_mult, 1),
                         cost_bps=round(cost.roundtrip_bps(h.maker_entry,
                                                           h.maker_entry), 1),
                         cost_to_stop=round(r, 3),
                         economic=bool(r <= 1.0 / 3.0),
                         note=""))
    return rows


def active_horizons(rows: list) -> list:
    """Horizon keys that pass the pre-trade economics screen."""
    return [r["horizon"] for r in rows if r.get("economic") is not False]
