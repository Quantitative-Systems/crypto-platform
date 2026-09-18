import enum
import numpy as np
import pandas as pd
from typing import Tuple

class RegimeState(enum.Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


def _calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average Directional Index (ADX) without external dependencies."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up = high - high.shift(1)
    down = low.shift(1) - low

    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Welles Wilder uses a smoothed moving average, which is similar to EMA with alpha=1/period
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx.fillna(0)


def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def detect_regime(df: pd.DataFrame, adx_period: int = 14, adx_threshold: float = 25.0) -> pd.Series:
    """
    Returns a pd.Series of RegimeState enums mapping to each timestamp.
    
    Logic:
    - If ADX > adx_threshold and close > EMA(50): TRENDING_UP
    - If ADX > adx_threshold and close < EMA(50): TRENDING_DOWN
    - If ADX <= adx_threshold:
        Check ATR percentile (rolling 100).
        - If ATR > 75th percentile: HIGH_VOLATILITY
        - If ATR < 25th percentile: LOW_VOLATILITY
        - Else: RANGING
    """
    adx = _calc_adx(df, period=adx_period)
    close = df["close"]
    ema50 = close.ewm(span=50, adjust=False).mean()
    
    atr = _calc_atr(df, period=14)
    atr_pct = atr.rolling(100, min_periods=20).rank(pct=True)
    
    # We will build an array of states
    states = np.empty(len(df), dtype=object)
    
    # Conditions
    trend_up = (adx > adx_threshold) & (close > ema50)
    trend_down = (adx > adx_threshold) & (close < ema50)
    
    high_vol = (adx <= adx_threshold) & (atr_pct > 0.75)
    low_vol = (adx <= adx_threshold) & (atr_pct < 0.25)
    ranging = (adx <= adx_threshold) & (atr_pct >= 0.25) & (atr_pct <= 0.75)
    
    states[trend_up] = RegimeState.TRENDING_UP
    states[trend_down] = RegimeState.TRENDING_DOWN
    states[high_vol] = RegimeState.HIGH_VOLATILITY
    states[low_vol] = RegimeState.LOW_VOLATILITY
    states[ranging] = RegimeState.RANGING
    
    # Default fallback for NaNs or early windows
    states[pd.isna(states)] = RegimeState.RANGING
    
    return pd.Series(states, index=df.index)
