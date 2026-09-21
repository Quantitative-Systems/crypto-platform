"""QCP Platform — trade contracts and the shared directional resolver.

Every directional strategy is reduced to two boolean arrays (long_sig,
short_sig) plus risk parameters, then resolved by ONE shared function so that
execution realism is provably identical across all horizons and families:

  * entry  : next bar's OPEN after the signal bar closes (never the signal bar)
  * stop   : atr_mult x ATR at the signal bar (fixed, not re-fitted)
  * target : target_r x stop distance
  * ties   : if a bar touches both stop and target, the STOP is assumed first
             (adverse-first) — the conservative convention
  * costs  : fee + slippage + half spread on BOTH sides, always
  * size   : risk-based, so 1R = risk_frac of reference equity
  * one open position per (strategy, symbol) at a time

R-multiples are scale-free, so the portfolio layer can apply its own risk
budget, allocation weights and drawdown throttle without re-simulating.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .costs import DEFAULT, CostModel


@dataclass
class Trade:
    strategy: str
    symbol: str
    horizon: str
    direction: int          # +1 long, -1 short
    entry_ts: int
    exit_ts: int
    entry_px: float
    exit_px: float
    stop_px: float
    target_px: float
    r_multiple: float       # net P&L in units of planned risk
    exit_reason: str
    mfe_r: float = 0.0
    mae_r: float = 0.0
    bars_held: int = 0
    meta: dict = field(default_factory=dict)


@dataclass
class BookResult:
    """Per-strategy simulation output expressed in R units."""
    strategy: str
    horizon: str
    trades: List[Trade] = field(default_factory=list)
    signal_count: int = 0
    skipped_cost: int = 0

    @property
    def n(self) -> int:
        return len(self.trades)

    @property
    def rs(self) -> np.ndarray:
        return (np.array([t.r_multiple for t in self.trades], dtype=float)
                if self.trades else np.array([]))

    @property
    def expectancy_r(self) -> float:
        r = self.rs
        return float(r.mean()) if len(r) else 0.0

    @property
    def total_r(self) -> float:
        r = self.rs
        return float(r.sum()) if len(r) else 0.0

    @property
    def win_rate(self) -> float:
        r = self.rs
        return float((r > 0).mean()) if len(r) else 0.0

    @property
    def profit_factor(self) -> float:
        r = self.rs
        if not len(r):
            return 0.0
        w, ls = r[r > 0].sum(), -r[r < 0].sum()
        if ls <= 0:
            return float("inf") if w > 0 else 0.0
        return float(w / ls)

    @property
    def max_dd_r(self) -> float:
        r = self.rs
        if not len(r):
            return 0.0
        cum = np.cumsum(r)
        return float(np.max(np.maximum.accumulate(cum) - cum))

    @property
    def sharpe_trade(self) -> float:
        r = self.rs
        if len(r) < 2 or r.std(ddof=0) == 0:
            return 0.0
        return float(r.mean() / r.std(ddof=0) * np.sqrt(len(r)))

    def summary(self) -> dict:
        return dict(strategy=self.strategy, horizon=self.horizon, n=self.n,
                    expectancy_r=round(self.expectancy_r, 4),
                    total_r=round(self.total_r, 2),
                    win_rate=round(self.win_rate, 3),
                    profit_factor=round(self.profit_factor, 3),
                    max_dd_r=round(self.max_dd_r, 2),
                    signals=self.signal_count, skipped_cost=self.skipped_cost)


def resolve_trades(strategy: str, symbol: str, horizon: str,
                   o, h, l, c, close_ts, atr_arr, long_sig, short_sig,
                   atr_mult: float, target_r: float, max_hold_bars: int,
                   cost: Optional[CostModel] = None,
                   maker_entry: bool = False,
                   min_stop_bps: float = 0.0,
                   allow_short: bool = True,
                   max_trades: int = 0,
                   trail_atr_mult: float = 0.0,
                   exit_long=None, exit_short=None) -> BookResult:
    """Resolve boolean signals into cost-included trades with R accounting.

    `exit_long`/`exit_short` (optional boolean arrays) support condition exits
    (rank drop, trend break). A condition true at the CLOSE of bar j exits at
    the OPEN of bar j+1, matching the entry convention.
    """
    cost = cost or DEFAULT
    n = len(c)
    o = np.asarray(o, dtype=float); h = np.asarray(h, dtype=float)
    l = np.asarray(l, dtype=float); c = np.asarray(c, dtype=float)
    atr_arr = np.asarray(atr_arr, dtype=float)
    long_sig = np.asarray(long_sig, dtype=bool)
    short_sig = np.asarray(short_sig, dtype=bool)
    if not allow_short:
        short_sig = np.zeros_like(short_sig)

    res = BookResult(strategy=strategy, horizon=horizon)
    idx = np.flatnonzero(long_sig | short_sig)
    res.signal_count = int(len(idx))
    if len(idx) == 0:
        return res

    rt_bps = cost.roundtrip_bps(maker_entry, maker_entry)
    slip = 0.0 if maker_entry else cost.slip_bps / 1e4
    ex_l = np.asarray(exit_long, dtype=bool) if exit_long is not None else None
    ex_s = np.asarray(exit_short, dtype=bool) if exit_short is not None else None
    busy_until = -1
    for i in idx:
        i = int(i)
        if i < 1 or i > n - 2 or i < busy_until:
            continue
        if max_trades and len(res.trades) >= max_trades:
            break
        a = atr_arr[i]
        if not np.isfinite(a) or a <= 0 or not np.isfinite(o[i + 1]) or o[i + 1] <= 0:
            continue
        stop_dist = atr_mult * a
        if stop_dist <= 0:
            continue
        entry = float(o[i + 1])
        stop_bps = stop_dist / entry * 1e4
        if stop_bps < min_stop_bps:
            res.skipped_cost += 1
            continue
        d = 1 if long_sig[i] else -1
        stop = entry - d * stop_dist
        target = entry + d * target_r * stop_dist
        fill_e = entry * (1 + d * slip)
        end = min(n - 1, i + 1 + max_hold_bars)
        exit_px = None
        reason = None
        mfe = 0.0; mae = 0.0
        cur_stop = stop
        for j in range(i + 1, end + 1):
            hi, lo = float(h[j]), float(l[j])
            if d == 1:
                mfe = max(mfe, (hi - fill_e) / stop_dist)
                mae = max(mae, (fill_e - lo) / stop_dist)
                if lo <= cur_stop:
                    exit_px = cur_stop
                    reason = "SL" if cur_stop == stop else "TRAIL"
                    end = j
                    break
                if hi >= target:
                    exit_px = target; reason = "TP"; end = j; break
                if trail_atr_mult > 0 and np.isfinite(atr_arr[j]):
                    cur_stop = max(cur_stop, hi - trail_atr_mult * float(atr_arr[j]))
            else:
                mfe = max(mfe, (fill_e - lo) / stop_dist)
                mae = max(mae, (hi - fill_e) / stop_dist)
                if hi >= cur_stop:
                    exit_px = cur_stop
                    reason = "SL" if cur_stop == stop else "TRAIL"
                    end = j
                    break
                if lo <= target:
                    exit_px = target; reason = "TP"; end = j; break
                if trail_atr_mult > 0 and np.isfinite(atr_arr[j]):
                    cur_stop = min(cur_stop, lo + trail_atr_mult * float(atr_arr[j]))
            long_exit = ex_l is not None and d == 1 and bool(ex_l[j])
            short_exit = ex_s is not None and d == -1 and bool(ex_s[j])
            if (long_exit or short_exit) and j + 1 < n:
                exit_px = float(o[j + 1])
                reason = "SIGNAL"
                end = j + 1
                break
        if exit_px is None:
            exit_px = float(c[end])
            reason = "TIME"
        fill_x = exit_px * (1 - d * slip)
        gross_bps = (fill_x - fill_e) / entry * 1e4 * d
        net_bps = gross_bps - rt_bps
        r_mult = (net_bps / 1e4 * entry) / stop_dist
        res.trades.append(Trade(
            strategy=strategy, symbol=symbol, horizon=horizon, direction=d,
            entry_ts=int(close_ts[i + 1]), exit_ts=int(close_ts[end]),
            entry_px=float(fill_e), exit_px=float(fill_x),
            stop_px=float(stop), target_px=float(target),
            r_multiple=float(r_mult), exit_reason=reason,
            mfe_r=float(mfe), mae_r=float(mae), bars_held=int(end - (i + 1)),
            meta=dict(stop_bps=round(stop_bps, 1), net_bps=round(net_bps, 1),
                      gross_bps=round(gross_bps, 1))))
        busy_until = end + 1
    return res
