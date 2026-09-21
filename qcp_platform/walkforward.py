"""QCP Platform — walk-forward protocol (the anti-overfit spine).

Protocol, applied identically to every strategy, asset and horizon:

    DEV  (first 60% of bars)  -> parameter selection happens HERE, only here
    VAL  (next 20%)           -> the DEV winner must still work here, untouched
    OOS  (final 20%)          -> reported once, never used for any decision
    ROLL                      -> the same windows advanced by 10% and re-run;
                                 a strategy that only works in one window is
                                 noise, and the rolling pass is what exposes it

Nothing in this module may read OOS when choosing parameters. That single rule
is the difference between a research platform and a curve-fit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np


@dataclass
class Windows:
    dev: slice
    val: slice
    oos: slice
    n: int

    def label(self) -> str:
        return (f"dev[{self.dev.start}:{self.dev.stop}] "
                f"val[{self.val.start}:{self.val.stop}] "
                f"oos[{self.oos.start}:{self.oos.stop}]")


def make_windows(n: int, dev: float = 0.60, val: float = 0.20) -> Windows:
    a = int(n * dev)
    b = int(n * (dev + val))
    return Windows(dev=slice(0, a), val=slice(a, b), oos=slice(b, n), n=n)


def rolling_windows(n: int, dev: float = 0.60, val: float = 0.20,
                    step: float = 0.10) -> List[Windows]:
    """Advance the whole window by `step` of the sample, keeping sizes fixed."""
    size = int(n * (1.0 - step))
    if size < 200:
        return []
    out = []
    start = 0
    while start + size <= n:
        out.append(make_windows_sized(start, size, dev, val))
        start += int(n * step)
    return out


def make_windows_sized(start: int, size: int, dev: float = 0.60,
                       val: float = 0.20) -> Windows:
    a = start + int(size * dev)
    b = start + int(size * (dev + val))
    return Windows(dev=slice(start, a), val=slice(a, b),
                   oos=slice(b, start + size), n=size)


@dataclass
class Selection:
    """Result of a DEV->VAL selection round for one (strategy, symbol)."""
    strategy: str
    symbol: str
    horizon: str
    params: dict = field(default_factory=dict)
    dev_exp: float = 0.0
    dev_n: int = 0
    val_exp: float = 0.0
    val_n: int = 0
    oos_exp: float = 0.0
    oos_n: int = 0
    dev_total_r: float = 0.0
    val_total_r: float = 0.0
    oos_total_r: float = 0.0
    chosen_on_dev: bool = True
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        return dict(strategy=self.strategy, symbol=self.symbol,
                    horizon=self.horizon, dev_n=self.dev_n,
                    dev_exp=round(self.dev_exp, 4), val_n=self.val_n,
                    val_exp=round(self.val_exp, 4), oos_n=self.oos_n,
                    oos_exp=round(self.oos_exp, 4),
                    dev_total_r=round(self.dev_total_r, 2),
                    val_total_r=round(self.val_total_r, 2),
                    oos_total_r=round(self.oos_total_r, 2),
                    params=self.params, notes=self.notes, **self.extra)


def select_params(grid: List[dict], simulate, min_trades: int = 30,
                  rank: str = "expectancy") -> tuple:
    """Pick the DEV-best parameter set. Returns (params, BookResult) or (None, None).

    `simulate(params)` must return a BookResult already restricted to the DEV
    window (the caller owns windowing). Selection never sees VAL or OOS.
    """
    best = None
    best_score = -np.inf
    best_res = None
    for params in grid:
        res = simulate(params)
        if res is None or res.n < min_trades:
            continue
        r = res.rs
        if rank == "total":
            score = float(r.sum())
        elif rank == "sharpe":
            score = res.sharpe_trade
        else:
            score = float(r.mean())
        if score > best_score:
            best_score = score
            best = params
            best_res = res
    return best, best_res


def slice_book(book, lo_ts: int, hi_ts: int):
    """Restrict a BookResult to trades whose EXIT falls in [lo_ts, hi_ts)."""
    from .engine import BookResult
    out = BookResult(strategy=book.strategy, horizon=book.horizon)
    out.signal_count = book.signal_count
    out.skipped_cost = book.skipped_cost
    out.trades = [t for t in book.trades if lo_ts <= t.exit_ts < hi_ts]
    return out


def window_bounds(close_ts: np.ndarray, w: Windows) -> tuple:
    """(lo_ts, hi_ts) pairs for dev/val/oos slices."""
    idx = lambda s: (int(close_ts[max(0, s.start)]), int(close_ts[min(len(close_ts) - 1, max(0, s.stop - 1))] + 1))
    return idx(w.dev), idx(w.val), idx(w.oos)


def consistency_wfr(dev_exp: float, val_exp: float, oos_exp: float) -> float:
    """Walk-forward ratio: fraction of consecutive windows that keep the sign.

    A strategy whose DEV edge does not survive VAL/OOS scores below 1.0; the
    promotion gate requires >= 0.30, i.e. at least the VAL leg holds up.
    """
    sign = np.sign(dev_exp)
    if sign == 0:
        return 0.0
    kept = 0
    steps = 0
    if np.sign(val_exp) == sign:
        kept += 1
    steps += 1
    if np.sign(oos_exp) == sign:
        kept += 1
    steps += 1
    return kept / steps if steps else 0.0

