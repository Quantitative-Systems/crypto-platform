"""Crypto Trading Platform — causal market regime classification.

Regimes exist so capital can be routed to a family that is actually suited to
current conditions (trend vs range vs high-vol stress) instead of running one
rule set through all weathers. All outputs are causal.
"""
from __future__ import annotations

import numpy as np

from . import indicators as ind

TREND_UP = 1
RANGE = 0
TREND_DN = -1

REGIME_NAMES = {1: "TREND_UP", 0: "RANGE", -1: "TREND_DN"}


def trend_state(c, h, l, adx_min: float = 20.0, slope_min: float = 0.01,
                span: int = 50) -> np.ndarray:
    """+1 uptrend, 0 range/chop, -1 downtrend. Causal.

    Requires BOTH a directional EMA stack and enough directional movement
    (ADX) so a low-vol drift is not mistaken for a trend.
    """
    c = np.asarray(c, dtype=float)
    f = ind.ema(c, max(5, span // 2))
    s = ind.ema(c, span)
    a = ind.adx(h, l, c, 14)
    sl = ind.ema_slope(c, span, max(3, span // 5))
    up = (f > s) & (np.nan_to_num(sl, nan=0.0) > slope_min)
    dn = (f < s) & (np.nan_to_num(sl, nan=0.0) < -slope_min)
    strong = np.nan_to_num(a, nan=0.0) >= adx_min
    out = np.zeros(len(c), dtype=float)
    out[up & strong] = TREND_UP
    out[dn & strong] = TREND_DN
    out[: span + 5] = 0.0
    return out


def vol_regime(c, n: int = 20, lookback: int = 250) -> np.ndarray:
    """Volatility percentile in [0,1] (>=0.8 = stressed). Causal."""
    v = ind.realized_vol(c, n, ann=365)
    p = ind.percentile_rank(np.nan_to_num(v, nan=np.nan), lookback)
    return np.nan_to_num(p, nan=0.5)


def stress_flag(c, n: int = 20, lookback: int = 250, thresh: float = 0.85) -> np.ndarray:
    """True when volatility sits in the top tail (crash / squeeze conditions)."""
    return vol_regime(c, n, lookback) >= thresh


def breadth(close_mat: np.ndarray, span: int = 50) -> np.ndarray:
    """Fraction of assets trading above their own EMA(span), per timestamp.

    A cross-asset risk-appetite gauge: feeds the INVEST/POSITION allocation.
    """
    k, s = close_mat.shape
    above = np.zeros(k)
    cnt = np.zeros(k)
    for j in range(s):
        col = close_mat[:, j]
        e = ind.ema(col, span)
        ok = np.isfinite(col) & np.isfinite(e)
        above[ok] += (col[ok] > e[ok]).astype(float)
        cnt[ok] += 1.0
    return np.divide(above, cnt, out=np.full(k, 0.5), where=cnt > 0)


def regime_frame(c, h, l, close_mat: np.ndarray | None = None) -> dict:
    """Bundle of regime outputs used by the router."""
    tr = trend_state(c, h, l)
    vr = vol_regime(c)
    out = dict(trend=tr, vol_pct=vr, stress=vr >= 0.85)
    if close_mat is not None:
        out["breadth"] = breadth(close_mat)
    return out
