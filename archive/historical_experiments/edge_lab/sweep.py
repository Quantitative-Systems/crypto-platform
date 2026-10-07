"""Sweep runner part 1: grid + single-stream DEV select."""
from __future__ import annotations
import numpy as np
from .config import SETS_6, SPLIT_DEV, SPLIT_VAL, MIN_TRADES_DEV
from .data import load_stream
from .indicators import atr
from .families import (fam_trend_pullback, fam_breakout, fam_range_revert,
                       fam_supertrend_rider, htf_trend_ctx, _align_context)
from .engine import run_stream

PARAM_GRID = [
    ("TREND_PULLBACK", dict(fast=20, slow=50, rsi_len=14)),
    ("TREND_PULLBACK_F", dict(fast=12, slow=30, rsi_len=14)),
    ("BREAKOUT_20", dict(kind="breakout", lookback=20)),
    ("BREAKOUT_50", dict(kind="breakout", lookback=50)),
    ("RANGE_50", dict(kind="range", lookback=50)),
    ("SUPERTREND", dict(kind="supertrend", atr_len=10, factor=3.0)),
]
MAX_HOLD = {"SET_1": 30, "SET_2": 40, "SET_3": 40, "SET_4": 60,
            "SET_5": 60, "SET_6": 80}


def _split(n: int):
    d = int(n * SPLIT_DEV)
    v = int(n * SPLIT_VAL)
    return (0, d), (d, d + v), (d + v, n)


def _signals(pname, p, L, h_ctx, m_ctx):
    if pname.startswith("TREND"):
        return fam_trend_pullback(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, fast=p["fast"], slow=p["slow"], rsi_len=p["rsi_len"])
    if pname.startswith("BREAKOUT"):
        return fam_breakout(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, lookback=p["lookback"])
    if pname.startswith("RANGE"):
        return fam_range_revert(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, lookback=p["lookback"])
    return fam_supertrend_rider(
        L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
        h_ctx, m_ctx, atr_len=p["atr_len"], factor=p["factor"])
