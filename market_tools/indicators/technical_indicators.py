"""Market Tools & Technical Indicators Engine.

Provides canonical calculations for ATR, Realized Volatility, RSI, ADX, and Moving Averages.
"""
from __future__ import annotations

import numpy as np


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Average True Range (ATR)."""
    n = len(closes)
    if n < 2:
        return np.zeros(n)

    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    out = np.zeros(n)
    if n >= period:
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Relative Strength Index (RSI)."""
    n = len(closes)
    if n < period + 1:
        return np.full(n, 50.0)

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    out = np.full(n, 50.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))

    return out


def realized_volatility(closes: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculate rolling annualized realized volatility from log returns."""
    n = len(closes)
    if n < period + 1:
        return np.zeros(n)
    log_ret = np.diff(np.log(np.maximum(closes, 1e-8)))
    out = np.zeros(n)
    for i in range(period, n):
        out[i] = float(np.std(log_ret[i - period:i]) * np.sqrt(365.25 * 24))
    return out


def ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    n = len(values)
    if n == 0:
        return np.array([])
    alpha = 2.0 / (period + 1.0)
    out = np.zeros(n, dtype=float)
    out[0] = values[0]
    for i in range(1, n):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


def sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    n = len(values)
    if n == 0:
        return np.array([])
    out = np.zeros(n, dtype=float)
    for i in range(n):
        start = max(0, i - period + 1)
        out[i] = float(np.mean(values[start:i + 1]))
    return out
