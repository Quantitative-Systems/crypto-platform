"""Crypto Trading Platform — vectorized, causal indicators.

All functions return float arrays the same length as input, aligned to the
CLOSE of bar i. A value at index i is computable using bars 0..i only, so any
array element may be read at bar i without look-ahead. Leading warm-up regions
are NaN and must be masked by callers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _s(x) -> pd.Series:
    return x if isinstance(x, pd.Series) else pd.Series(np.asarray(x, dtype=float))


def _w(x) -> np.ndarray:
    """Writable float array — pandas/pyarrow can hand back read-only buffers."""
    a = np.asarray(x, dtype=float)
    return a if a.flags.writeable else a.copy()


def sma(x, n: int) -> np.ndarray:
    return _w(_s(x).rolling(n, min_periods=n).mean())


def ema(x, n: int) -> np.ndarray:
    return _w(_s(x).ewm(span=n, adjust=False).mean())


def rma(x, n: int) -> np.ndarray:
    """Wilder smoothing (used by ATR/RSI/ADX)."""
    return _w(_s(x).ewm(alpha=1.0 / n, adjust=False).mean())


def true_range(h, l, c) -> np.ndarray:
    h, l, c = _s(h), _s(l), _s(c)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return _w(tr)


def atr(h, l, c, n: int = 14) -> np.ndarray:
    tr = true_range(h, l, c)
    out = rma(tr, n)
    out[:n] = np.nan
    return out


def rsi(c, n: int = 14) -> np.ndarray:
    d = _s(c).diff()
    up = rma(d.clip(lower=0).fillna(0.0), n)
    dn = rma((-d.clip(upper=0)).fillna(0.0), n)
    rs = np.divide(up, dn, out=np.full_like(up, np.nan), where=dn > 0)
    out = 100.0 - 100.0 / (1.0 + rs)
    return np.where(dn <= 0, 100.0, out).copy()


def adx(h, l, c, n: int = 14) -> np.ndarray:
    h, l, c = _s(h), _s(l), _s(c)
    up = h.diff()
    dn = -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n)
    pdi = 100.0 * rma(plus, n) / np.where(tr == 0, np.nan, tr)
    mdi = 100.0 * rma(minus, n) / np.where(tr == 0, np.nan, tr)
    dx = 100.0 * np.abs(pdi - mdi) / np.where((pdi + mdi) == 0, np.nan, pdi + mdi)
    out = rma(dx, n)
    out[: 2 * n] = np.nan
    return out


def donchian(h, l, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Upper/lower channel of the PRIOR n bars (excludes current bar) -> causal."""
    hh = _w(_s(h).rolling(n, min_periods=n).max().shift(1))
    ll = _w(_s(l).rolling(n, min_periods=n).min().shift(1))
    return hh, ll


def rolling_std(x, n: int) -> np.ndarray:
    return _w(_s(x).rolling(n, min_periods=n).std(ddof=0))


def zscore(x, n: int) -> np.ndarray:
    s = _s(x)
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return _w(((s - m) / sd.replace(0, np.nan)))


def roc(x, n: int) -> np.ndarray:
    """Rate of change over n bars (fractional)."""
    s = _s(x)
    return _w((s / s.shift(n) - 1.0))


def percentile_rank(x, n: int) -> np.ndarray:
    """Fractional rank of the current value within the trailing n values."""
    s = _s(x)
    mn = s.rolling(n, min_periods=max(5, n // 4)).min()
    mx = s.rolling(n, min_periods=max(5, n // 4)).max()
    return _w(((s - mn) / (mx - mn).replace(0, np.nan)).clip(0.0, 1.0))


def realized_vol(c, n: int = 20, ann: int = 365) -> np.ndarray:
    """Annualized close-to-close volatility (fractional)."""
    r = _s(c).pct_change()
    return _w(r.rolling(n, min_periods=n).std(ddof=0) * np.sqrt(ann))


def supertrend_dir(h, l, c, n: int = 10, mult: float = 3.0) -> np.ndarray:
    """+1/-1 trend direction from Supertrend (causal, sequential)."""
    h, l, c = (np.asarray(x, dtype=float) for x in (h, l, c))
    a = atr(h, l, c, n)
    hl2 = (h + l) / 2.0
    upper = hl2 + mult * a
    lower = hl2 - mult * a
    m = len(c)
    out = np.zeros(m, dtype=float)
    fu = np.full(m, np.nan)
    fl = np.full(m, np.nan)
    d = 1.0
    for i in range(1, m):
        if np.isnan(a[i]):
            continue
        fu[i] = upper[i] if (np.isnan(fu[i - 1]) or upper[i] < fu[i - 1]
                             or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (np.isnan(fl[i - 1]) or lower[i] > fl[i - 1]
                             or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if c[i] > fu[i - 1] if not np.isnan(fu[i - 1]) else False:
            d = 1.0
        elif c[i] < fl[i - 1] if not np.isnan(fl[i - 1]) else False:
            d = -1.0
        out[i] = d
    return out


def ema_slope(x, n: int = 50, lookback: int = 10) -> np.ndarray:
    """Fractional slope of EMA(n) over `lookback` bars."""
    e = _s(ema(x, n))
    prev = e.shift(lookback)
    return _w((e / prev - 1.0))


def rolling_max(x, n: int) -> np.ndarray:
    return _w(_s(x).rolling(n, min_periods=n).max())


def rolling_min(x, n: int) -> np.ndarray:
    return _w(_s(x).rolling(n, min_periods=n).min())


def drawdown_from_ath(c) -> np.ndarray:
    """Fractional drawdown from running all-time high (>=0)."""
    s = _s(c)
    peak = s.cummax()
    return (peak - s) / peak


def correlation(a, b, n: int) -> np.ndarray:
    return _w(_s(a).rolling(n, min_periods=n).corr(_s(b)))
