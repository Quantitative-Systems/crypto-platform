"""
Fully vectorized numpy-based indicator calculations for maximum performance.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from market_intelligence.primitives import Candle


def supertrend_numpy(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                     atr_length: int = 6, factor: float = 5.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized Supertrend calculation.
    Returns (supertrend_values, directions) arrays.
    direction: 1 = bullish, -1 = bearish
    """
    n = len(closes)
    if n < atr_length:
        return np.zeros(n), np.ones(n, dtype=int)

    # True Range
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    hl = highs[1:] - lows[1:]
    hc = np.abs(highs[1:] - closes[:-1])
    lc = np.abs(lows[1:] - closes[:-1])
    tr[1:] = np.maximum(np.maximum(hl, hc), lc)

    # ATR using Wilder's smoothing (RMA)
    atr = np.zeros(n)
    atr[atr_length - 1] = np.mean(tr[:atr_length])
    for i in range(atr_length, n):
        atr[i] = (atr[i-1] * (atr_length - 1) + tr[i]) / atr_length

    hl2 = (highs + lows) / 2.0
    basic_ub = hl2 + factor * atr
    basic_lb = hl2 - factor * atr

    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.ones(n, dtype=int)

    final_ub[0] = basic_ub[0]
    final_lb[0] = basic_lb[0]
    supertrend[0] = final_lb[0]
    direction[0] = 1

    for i in range(1, n):
        if basic_ub[i] < final_ub[i-1] or closes[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]

        if basic_lb[i] > final_lb[i-1] or closes[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]

        if supertrend[i-1] == final_ub[i-1]:
            if closes[i] <= final_ub[i]:
                direction[i] = -1
                supertrend[i] = final_ub[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lb[i]
        else:
            if closes[i] >= final_lb[i]:
                direction[i] = 1
                supertrend[i] = final_lb[i]
            else:
                direction[i] = -1
                supertrend[i] = final_ub[i]

    return supertrend, direction


def stochastic_numpy(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                     k_length: int = 25, k_smooth: int = 5, d_smooth: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized Stochastic calculation.
    Returns (k, d) arrays.
    """
    n = len(closes)
    if n < k_length:
        return np.full(n, 50.0), np.full(n, 50.0)

    # Fast %K using rolling window
    fast_k = np.full(n, 50.0)
    for i in range(k_length - 1, n):
        window_low = np.min(lows[i - k_length + 1:i + 1])
        window_high = np.max(highs[i - k_length + 1:i + 1])
        if window_high == window_low:
            fast_k[i] = 50.0
        else:
            fast_k[i] = ((closes[i] - window_low) / (window_high - window_low)) * 100.0

    # Smooth %K (SMA)
    k = np.full(n, 50.0)
    start_k = k_length - 1 + k_smooth - 1
    for i in range(start_k, n):
        k[i] = np.mean(fast_k[i - k_smooth + 1:i + 1])

    # Smooth %D (SMA of K)
    d = np.full(n, 50.0)
    start_d = start_k + d_smooth - 1
    for i in range(start_d, n):
        d[i] = np.mean(k[i - d_smooth + 1:i + 1])

    return k, d


def compute_indicators_fast(candles: List[Candle]) -> Dict[str, Any]:
    """Compute all indicators using vectorized numpy."""
    n = len(candles)
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    closes = np.array([c.close for c in candles])
    timestamps = np.array([c.timestamp for c in candles], dtype=np.int64)

    st_val, st_dir = supertrend_numpy(highs, lows, closes, 6, 5.0)
    k_arr, d_arr = stochastic_numpy(highs, lows, closes, 25, 5, 3)

    return {
        "ts": timestamps,
        "high": highs,
        "low": lows,
        "close": closes,
        "st_val": st_val,
        "st_dir": st_dir,
        "k": k_arr,
        "d": d_arr,
        "interval": int(timestamps[1] - timestamps[0]) if n > 1 else 0,
    }
