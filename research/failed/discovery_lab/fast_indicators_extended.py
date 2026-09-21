"""
PROJECT TOP1 — Extended High-Performance Vectorized Technical Indicators.

Implements pure NumPy / Numba-ready indicator calculations for the 8 strategy families:
1. Exponential Moving Average (EMA)
2. Average True Range (ATR)
3. Relative Strength Index (RSI)
4. Donchian Channels (Breakout)
5. Bollinger Bands & Squeeze (Volatility Expansion & Mean Reversion)
6. Keltner Channels
7. Average Directional Index (ADX - Regime Detection)
"""

import numpy as np
from typing import Tuple, Dict, Any


def ema_numpy(data: np.ndarray, period: int) -> np.ndarray:
    """Vectorized / recursive Exponential Moving Average."""
    n = len(data)
    ema = np.empty(n, dtype=np.float64)
    if n == 0:
        return ema
    if n < period:
        ema[:] = np.nan
        return ema

    multiplier = 2.0 / (period + 1.0)
    # Seed with SMA
    ema[:period - 1] = np.nan
    ema[period - 1] = np.mean(data[:period])

    for i in range(period, n):
        ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def atr_numpy(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range using Wilder's smoothing."""
    n = len(close)
    atr = np.empty(n, dtype=np.float64)
    if n < 2:
        atr[:] = np.nan
        return atr

    tr = np.empty(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    if n < period:
        atr[:] = np.nan
        return atr

    atr[:period - 1] = np.nan
    atr[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period
    for i in range(period, n):
        atr[i] = atr[i - 1] * (1.0 - alpha) + tr[i] * alpha
    return atr


def rsi_numpy(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index using Wilder's smoothing."""
    n = len(close)
    rsi = np.empty(n, dtype=np.float64)
    if n <= period:
        rsi[:] = np.nan
        return rsi

    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)

    rsi[:period] = np.nan
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    alpha = 1.0 / period
    for i in range(period, len(delta)):
        avg_gain = avg_gain * (1.0 - alpha) + gains[i] * alpha
        avg_loss = avg_loss * (1.0 - alpha) + losses[i] * alpha
        idx = i + 1
        if avg_loss == 0.0:
            rsi[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[idx] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def donchian_numpy(high: np.ndarray, low: np.ndarray, period: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Donchian Channels: upper band (highest high), lower band (lowest low), mid band.
    Upper and lower exclude current bar to avoid lookahead.
    """
    n = len(high)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)
    mid = np.full(n, np.nan, dtype=np.float64)

    for i in range(period, n):
        # Lookback over previous [i-period, i) bars
        h_win = high[i - period:i]
        l_win = low[i - period:i]
        upper[i] = np.max(h_win)
        lower[i] = np.min(l_win)
        mid[i] = (upper[i] + lower[i]) / 2.0

    return upper, lower, mid


def bollinger_bands_numpy(close: np.ndarray, period: int = 20, num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands: middle (SMA), upper, lower."""
    n = len(close)
    mid = np.full(n, np.nan, dtype=np.float64)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return mid, upper, lower

    # Rolling mean and std
    for i in range(period - 1, n):
        win = close[i - period + 1:i + 1]
        m = np.mean(win)
        s = np.std(win)
        mid[i] = m
        upper[i] = m + num_std * s
        lower[i] = m - num_std * s

    return mid, upper, lower


def adx_numpy(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average Directional Index (ADX) for regime detection."""
    n = len(close)
    adx = np.full(n, np.nan, dtype=np.float64)
    if n < 2 * period + 1:
        return adx

    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # TR
    tr = np.empty(n - 1, dtype=np.float64)
    for i in range(len(tr)):
        hl = high[i + 1] - low[i + 1]
        hc = abs(high[i + 1] - close[i])
        lc = abs(low[i + 1] - close[i])
        tr[i] = max(hl, hc, lc)

    # Smooth TR, plus_dm, minus_dm
    smooth_tr = np.empty(len(tr), dtype=np.float64)
    smooth_pdm = np.empty(len(tr), dtype=np.float64)
    smooth_mdm = np.empty(len(tr), dtype=np.float64)

    smooth_tr[:period - 1] = np.nan
    smooth_pdm[:period - 1] = np.nan
    smooth_mdm[:period - 1] = np.nan

    smooth_tr[period - 1] = np.sum(tr[:period])
    smooth_pdm[period - 1] = np.sum(plus_dm[:period])
    smooth_mdm[period - 1] = np.sum(minus_dm[:period])

    for i in range(period, len(tr)):
        smooth_tr[i] = smooth_tr[i - 1] - (smooth_tr[i - 1] / period) + tr[i]
        smooth_pdm[i] = smooth_pdm[i - 1] - (smooth_pdm[i - 1] / period) + plus_dm[i]
        smooth_mdm[i] = smooth_mdm[i - 1] - (smooth_mdm[i - 1] / period) + minus_dm[i]

    dx = np.empty(len(tr), dtype=np.float64)
    dx[:period - 1] = np.nan
    for i in range(period - 1, len(tr)):
        pdi = 100.0 * smooth_pdm[i] / smooth_tr[i] if smooth_tr[i] > 0 else 0.0
        mdi = 100.0 * smooth_mdm[i] / smooth_tr[i] if smooth_tr[i] > 0 else 0.0
        denom = pdi + mdi
        dx[i] = 100.0 * abs(pdi - mdi) / denom if denom > 0 else 0.0

    # ADX is Wilder's smoothing of DX
    start_adx = 2 * period - 1
    if len(dx) > start_adx:
        adx_val = np.mean(dx[period - 1:start_adx])
        adx[start_adx + 1] = adx_val
        for i in range(start_adx, len(dx)):
            adx_val = (adx_val * (period - 1) + dx[i]) / period
            adx[i + 1] = adx_val

    return adx
