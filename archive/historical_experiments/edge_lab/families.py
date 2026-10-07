"""Strategy families — causal signal generators on LTF + HTF/MTF context.

Each family emits (long[i], short[i]) using only data <= bar i close.
HTF/MTF context is aligned causally: context value at LTF bar i is the
last CLOSED HTF/MTF bar with close_time <= LTF close_time.
"""
from __future__ import annotations
import numpy as np
from .indicators import ema, rsi, donchian, supertrend_dir, atr


def _align_context(ltf_close_ts: np.ndarray, ctx_close_ts: np.ndarray,
                   ctx_vals: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(ctx_close_ts, ltf_close_ts, side="right") - 1
    idx = np.clip(idx, 0, len(ctx_vals) - 1)
    return ctx_vals[idx]


def fam_trend_pullback(o, h, l, c, ts, close_ts,
                       htf_dir_ctx, mtf_dir_ctx,
                       fast: int = 20, slow: int = 50,
                       rsi_len: int = 14, rsi_buy: float = 55.0,
                       rsi_sell: float = 45.0):
    f = ema(c, fast)
    s = ema(c, slow)
    r = rsi(c, rsi_len)
    bull_ctx = (htf_dir_ctx == 1) | (mtf_dir_ctx == 1)
    bear_ctx = (htf_dir_ctx == -1) | (mtf_dir_ctx == -1)
    long = (f > s) & (r >= rsi_buy - 10) & (r <= rsi_buy + 15) & bull_ctx
    short = (f < s) & (r <= rsi_sell + 10) & (r >= rsi_sell - 15) & bear_ctx
    long[:slow + 5] = False
    short[:slow + 5] = False
    return long, short


def fam_breakout(o, h, l, c, ts, close_ts, htf_dir_ctx, mtf_dir_ctx,
                 lookback: int = 20):
    hi, lo = donchian(h, l, lookback)
    brk_up = c > hi
    brk_dn = c < lo
    brk_up = np.nan_to_num(brk_up.astype(float), nan=0.0).astype(bool)
    brk_dn = np.nan_to_num(brk_dn.astype(float), nan=0.0).astype(bool)
    long = brk_up & ((htf_dir_ctx == 1) | (mtf_dir_ctx == 1))
    short = brk_dn & ((htf_dir_ctx == -1) | (mtf_dir_ctx == -1))
    long[:lookback + 2] = False
    short[:lookback + 2] = False
    return long, short


def fam_range_revert(o, h, l, c, ts, close_ts, htf_dir_ctx, mtf_dir_ctx,
                     lookback: int = 50):
    hi, lo = donchian(h, l, lookback)
    mid = (np.nan_to_num(hi, nan=np.nan) + np.nan_to_num(lo, nan=np.nan)) / 2
    long = (c < lo + 0.15 * (hi - lo)) & (c < mid)
    short = (c > hi - 0.15 * (hi - lo)) & (c > mid)
    valid = ~(np.isnan(hi) | np.isnan(lo))
    long = long & valid
    short = short & valid
    return long, short


def fam_supertrend_rider(o, h, l, c, ts, close_ts, htf_dir_ctx, mtf_dir_ctx,
                         atr_len: int = 10, factor: float = 3.0):
    d = supertrend_dir(h, l, c, atr_len, factor)
    long = (d == 1) & ((htf_dir_ctx == 1) | (mtf_dir_ctx == 1))
    short = (d == -1) & ((htf_dir_ctx == -1) | (mtf_dir_ctx == -1))
    long[:atr_len + 5] = False
    short[:atr_len + 5] = False
    return long, short


def htf_trend_ctx(h, l, c, fast: int = 20, slow: int = 50):
    f = ema(c, fast)
    s = ema(c, slow)
    return np.where(f > s, 1, np.where(f < s, -1, 0))
