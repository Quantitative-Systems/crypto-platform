"""Crypto Trading Platform — signal families across ALL horizons.

Directional families emit (long, short) boolean arrays and are resolved by
`engine.resolve_trades`. Allocation families (cross-sectional momentum, funding
carry, DCA accumulation) emit per-asset positions and are resolved by their own
routines but return the same `BookResult` contract, so the portfolio layer
treats every book identically.

Causality: HTF/MTF context is read via `data.align_causal`, i.e. only bars that
had already closed. Signals are evaluated on the LTF CLOSE; entry happens at the
following bar's OPEN inside the resolver.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from . import data as D
from . import indicators as ind
from . import regimes as reg


def _htf_dir(ltf_close_ts, htf: Dict, span: int) -> np.ndarray:
    """Causal HTF trend direction (+1/-1/0) aligned to LTF bars."""
    e_f = ind.ema(htf["c"], max(3, span // 2))
    e_s = ind.ema(htf["c"], span)
    htf2 = dict(htf)
    htf2["dir"] = np.where(e_f > e_s, 1.0, np.where(e_f < e_s, -1.0, 0.0))
    return np.nan_to_num(D.align_causal(ltf_close_ts, htf2, "dir"), nan=0.0)


def trend_strength(close: np.ndarray, span: int = 50) -> np.ndarray:
    """Normalized EMA spread in units of average absolute bar change."""
    c = np.asarray(close, dtype=float)
    f = ind.ema(c, max(3, span // 2))
    s = ind.ema(c, span)
    noise = ind.ema(np.abs(np.diff(c, prepend=c[0])), 14)
    return np.nan_to_num((f - s) / np.where(noise == 0, np.nan, noise), nan=0.0)


def efficiency_ratio(close: np.ndarray, n: int = 60) -> np.ndarray:
    """Kaufman efficiency: |net move| / sum(|bar moves|) over n bars, in [0,1].

    High = clean directional move. Low = chop that pays spread without travel.
    """
    c = np.asarray(close, dtype=float)
    net = np.abs(c - np.roll(c, n))
    path = np.abs(np.diff(c, prepend=c[0]))
    path_sum = np.convolve(path, np.ones(n), mode="full")[: len(c)]
    out = np.divide(net, path_sum, out=np.zeros_like(net), where=path_sum > 0)
    out[:n] = 0.0
    return np.clip(out, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 1. Trend / breakout  (INTRADAY, SWING, POSITION)
# ---------------------------------------------------------------------------
def sig_trend_breakout(d: Dict, atr_arr: np.ndarray, htf: Dict, mtf: Dict,
                       lookback: int = 50, atr_lb: int = 100,
                       ts_gate: float = 0.3, htf_span: int = 50,
                       vol_pct_min: float = 0.5,
                       require_quality: bool = False,
                       q_min: float = 0.55) -> Tuple[np.ndarray, np.ndarray]:
    """Donchian breakout gated by volatility expansion, trend strength and HTF."""
    c, h, l = d["c"], d["h"], d["l"]
    hi, lo = ind.donchian(h, l, lookback)
    brk_up = np.nan_to_num(c > hi, nan=False).astype(bool)
    brk_dn = np.nan_to_num(c < lo, nan=False).astype(bool)
    ap = ind.percentile_rank(np.nan_to_num(atr_arr, nan=np.nan), atr_lb)
    tstr = trend_strength(c, 50)
    hd = _htf_dir(d["close_ts"], htf, htf_span)
    md = _htf_dir(d["close_ts"], mtf, max(10, htf_span // 2))
    vol_ok = np.nan_to_num(ap, nan=0.5) >= vol_pct_min
    long = brk_up & vol_ok & (tstr > -ts_gate) & ((hd == 1) | (md == 1))
    short = brk_dn & vol_ok & (tstr < ts_gate) & ((hd == -1) | (md == -1))
    if require_quality:
        q = (efficiency_ratio(c, 60) * 0.5
             + np.clip(np.nan_to_num(ap, nan=0.5), 0, 1) * 0.5)
        long = long & (q >= q_min)
        short = short & (q >= q_min)
    long[: max(lookback, htf_span) + 5] = False
    short[: max(lookback, htf_span) + 5] = False
    return long, short


def sig_trend_rider(d: Dict, atr_arr: np.ndarray, htf: Dict, mtf: Dict,
                    fast: int = 20, slow: int = 50, ts_min: float = 0.5,
                    adx_min: float = 18.0,
                    pullback_max: float = 0.6) -> Tuple[np.ndarray, np.ndarray]:
    """Trend continuation entered on a shallow pullback (better R than chasing)."""
    c, h, l = d["c"], d["h"], d["l"]
    f = ind.ema(c, fast); s = ind.ema(c, slow)
    ts = trend_strength(c, slow)
    a = ind.adx(h, l, c, 14)
    hd = _htf_dir(d["close_ts"], htf, slow)
    md = _htf_dir(d["close_ts"], mtf, fast)
    ext = np.divide(c - f, np.where(atr_arr > 0, atr_arr, np.nan))
    trend_ok = np.nan_to_num(a, nan=0.0) >= adx_min
    long = ((f > s) & (ts >= ts_min) & trend_ok
            & (ext <= pullback_max) & ((hd == 1) | (md == 1)))
    short = ((f < s) & (ts <= -ts_min) & trend_ok
             & (ext >= -pullback_max) & ((hd == -1) | (md == -1)))
    long[: slow + 5] = False
    short[: slow + 5] = False
    return long, short


# ---------------------------------------------------------------------------
# 2. Mean reversion  (INTRADAY, SWING — range regimes only)
# ---------------------------------------------------------------------------
def sig_mean_revert(d: Dict, atr_arr: np.ndarray, htf: Dict, mtf: Dict,
                    band_n: int = 20, z_entry: float = 2.0,
                    rsi_len: int = 14, rsi_low: float = 30.0,
                    rsi_high: float = 70.0,
                    block_trend: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """Fade extensions beyond a volatility band, but never fight a real trend."""
    c, h, l = d["c"], d["h"], d["l"]
    mid = ind.ema(c, band_n)
    sd = ind.rolling_std(c, band_n)
    z = np.divide(c - mid, np.where(sd > 0, sd, np.nan))
    r = ind.rsi(c, rsi_len)
    tr = reg.trend_state(c, h, l) if block_trend else np.zeros(len(c))
    long = np.nan_to_num(z <= -z_entry, nan=False) & (r <= rsi_low) & (tr >= 0)
    short = np.nan_to_num(z >= z_entry, nan=False) & (r >= rsi_high) & (tr <= 0)
    long[: band_n + 5] = False
    short[: band_n + 5] = False
    return long, short


def sig_scalp_micro(d: Dict, atr_arr: np.ndarray, htf: Dict, mtf: Dict,
                    lookback: int = 12, vol_mult: float = 1.5,
                    rsi_len: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """Micro-breakout scalp. Included to be MEASURED, not to be believed.

    The pre-trade economics screen already flags this horizon as cost-blocked
    with taker fills; this family exists so the platform reports its real
    expectancy instead of an opinion about it.
    """
    c, h, l, v = d["c"], d["h"], d["l"], d["v"]
    hi = ind.rolling_max(h, lookback)
    lo = ind.rolling_min(l, lookback)
    vavg = ind.sma(v, 20)
    spike = np.nan_to_num(v > vol_mult * vavg, nan=False)
    r = ind.rsi(c, rsi_len)
    up = np.nan_to_num(c >= hi, nan=False) & spike & (r > 50) & (r < 80)
    dn = np.nan_to_num(c <= lo, nan=False) & spike & (r < 50) & (r > 20)
    up[: lookback + 5] = False
    dn[: lookback + 5] = False
    return up, dn


# ---------------------------------------------------------------------------
# 3. Grid / range harvesting  (INTRADAY — range regimes, maker fills)
# ---------------------------------------------------------------------------
def sig_grid_range(d: Dict, atr_arr: np.ndarray, htf: Dict, mtf: Dict,
                   band_n: int = 96, n_levels: int = 6,
                   max_adx: float = 22.0,
                   touch_buffer: float = 0.15) -> Tuple[np.ndarray, np.ndarray]:
    """Buy the lower rungs / sell the upper rungs of a trailing range.

    Grid trading only pays in a genuine range, so ADX must be low and the
    channel must be wide relative to ATR (otherwise the rungs sit inside the
    noise and every fill is a loss). Maker fills are assumed by the caller.
    """
    c, h, l = d["c"], d["h"], d["l"]
    hi = ind.rolling_max(h, band_n)
    lo = ind.rolling_min(l, band_n)
    width = hi - lo
    a = ind.adx(h, l, c, 14)
    rng_ok = np.nan_to_num(a, nan=99.0) <= max_adx
    wide_ok = np.nan_to_num(width >= n_levels * 2.0 * atr_arr, nan=False)
    pos = np.divide(c - lo, np.where(width > 0, width, np.nan))
    long = rng_ok & wide_ok & np.nan_to_num(pos <= touch_buffer, nan=False)
    short = rng_ok & wide_ok & np.nan_to_num(pos >= 1.0 - touch_buffer, nan=False)
    long[: band_n + 5] = False
    short[: band_n + 5] = False
    return long, short
