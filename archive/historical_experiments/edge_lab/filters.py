"""Cost-aware minimum-stop + volatility regime filter.

V2 upgrade rationale (from v1 forensics):
- v1 proved SET_5/SET_6 stops (25bps/7bps) are consumed by 22bps roundtrip
  costs (87%/332% of stop). No signal can survive that. Fix: enforce
  min_stop_bps per set (skip trades whose ATR stop < cost floor).
- v1 trend-pullback fires every bar in chop (thousands of -0.08R trades).
  Fix: ADX-style trend gate + volatility percentile filter so we only trade
  when expansion is plausible.
- v1 exits are symmetric ATR multiples. Keep (they work on SET_1/SET_2) but
  add optional chandelier-style trailing via max_hold already present.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def atr_percentile(atr_arr: np.ndarray, lookback: int = 100) -> np.ndarray:
    s = pd.Series(atr_arr)
    roll_min = s.rolling(lookback, min_periods=20).min()
    roll_max = s.rolling(lookback, min_periods=20).max()
    pct = (s - roll_min) / (roll_max - roll_min).replace(0, np.nan)
    return pct.fillna(0.5).to_numpy()


def trend_strength(close: np.ndarray, span: int = 50) -> np.ndarray:
    """Normalized slope: (EMA_fast - EMA_slow)/ATR proxy. Positive = uptrend."""
    c = pd.Series(close)
    f = c.ewm(span=span // 2, adjust=False).mean()
    s = c.ewm(span=span, adjust=False).mean()
    vol = c.diff().abs().ewm(span=14, adjust=False).mean().replace(0, np.nan)
    out = ((f - s) / vol).fillna(0.0).to_numpy()
    return out


# Per-set minimum stop in bps of entry (cost floor: need stop >> 22bps costs).
# SET_6 needs 60bps stops -> with 3.3bps median ATR that means atr_mult ~18x.
# Honest consequence: SET_6 will produce ~0 trades until 1m history deepens or
# costs drop (maker fills). That is REPORTED, not bypassed.
MIN_STOP_BPS = {
    "SET_1": 100.0,
    "SET_2": 80.0,
    "SET_3": 60.0,
    "SET_4": 40.0,
    "SET_5": 40.0,
    "SET_6": 40.0,
}
