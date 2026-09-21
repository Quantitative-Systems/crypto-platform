"""V2 families: cost-aware breakout + trend-expansion rider.

Key changes vs v1:
- Donchian breakout requires volatility expansion (ATR percentile gate):
  only trade breakouts when current ATR is above its median -> avoids chop.
- Trend rider requires trend_strength confirmation, not just EMA alignment.
- Signals are sparse by design (quality over quantity).
"""
from __future__ import annotations
import numpy as np
from .indicators import ema, donchian, supertrend_dir
from .filters import atr_percentile, trend_strength


def v2_breakout_expansion(o, h, l, c, ts, close_ts, htf_ctx, mtf_ctx,
                          atr_arr, lookback=50, atr_lb=100, ts_gate=0.3):
    hi, lo = donchian(h, l, lookback)
    brk_up = np.nan_to_num((c > hi).astype(float), nan=0.0).astype(bool)
    brk_dn = np.nan_to_num((c < lo).astype(float), nan=0.0).astype(bool)
    ap = atr_percentile(atr_arr, atr_lb)
    tstr = trend_strength(c, 50)
    vol_ok = ap >= 0.5
    long = brk_up & vol_ok & (tstr > -ts_gate) & ((htf_ctx == 1) | (mtf_ctx == 1))
    short = brk_dn & vol_ok & (tstr < ts_gate) & ((htf_ctx == -1) | (mtf_ctx == -1))
    long[:lookback + 2] = False
    short[:lookback + 2] = False
    return long, short


def v2_trend_expansion(o, h, l, c, ts, close_ts, htf_ctx, mtf_ctx,
                       atr_arr, fast=20, slow=50, ts_min=0.5):
    f = ema(c, fast)
    s = ema(c, slow)
    tstr = trend_strength(c, slow)
    ap = atr_percentile(atr_arr, 100)
    long = (f > s) & (tstr >= ts_min) & (ap >= 0.4) & ((htf_ctx == 1) | (mtf_ctx == 1))
    short = (f < s) & (tstr <= -ts_min) & (ap >= 0.4) & ((htf_ctx == -1) | (mtf_ctx == -1))
    # enter only on fresh cross to reduce repetition: price above fast EMA turn
    long[:slow + 5] = False
    short[:slow + 5] = False
    return long, short


def v2_supertrend_filtered(o, h, l, c, ts, close_ts, htf_ctx, mtf_ctx,
                           atr_arr, atr_len=10, factor=3.0):
    d = supertrend_dir(h, l, c, atr_len, factor)
    tstr = trend_strength(c, 50)
    ap = atr_percentile(atr_arr, 100)
    long = (d == 1) & (tstr > 0.2) & (ap >= 0.4) & ((htf_ctx == 1) | (mtf_ctx == 1))
    short = (d == -1) & (tstr < -0.2) & (ap >= 0.4) & ((htf_ctx == -1) | (mtf_ctx == -1))
    long[:atr_len + 5] = False
    short[:atr_len + 5] = False
    return long, short
