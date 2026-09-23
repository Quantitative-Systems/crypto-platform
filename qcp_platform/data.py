"""Crypto Trading Platform — data access, causal resampling, multi-asset panels.

Reads only the local cache (market_data/cache) so results are reproducible
offline. Every panel carries per-bar close timestamps; alignment to a higher
timeframe uses `align_causal`, which is the ONLY sanctioned way to use HTF data
(it selects the last HTF bar that had already CLOSED).
"""
from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional

import numpy as np

from market_data.data_manager import DataManager

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "12h": 43200,
    "1d": 86400, "1w": 604800,
    # `1M` is a 30-day bucket, not a calendar month. It exists so the INVEST
    # horizon has a slow context clock; it is never used for P&L accounting.
    "1M": 2592000,
}

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
          "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]

#: Process-lifetime cache of resampled/derived timeframes (never mutated in place).
_TF_CACHE: Dict[str, Dict[str, np.ndarray]] = {}


def _cache_path(symbol: str, timeframe: str) -> Optional[str]:
    try:
        p = DataManager.get_cache_filepath(symbol, timeframe)
    except Exception:
        p = os.path.join("market_data", "cache", f"binance_{symbol}_{timeframe}.json")
    return p if os.path.exists(p) else None


def load_ohlcv(symbol: str, timeframe: str) -> Optional[Dict[str, np.ndarray]]:
    """Return dict(ts, close_ts, o, h, l, c, v, interval) or None."""
    p = _cache_path(symbol, timeframe)
    if p is None:
        return None
    try:
        with open(p) as f:
            raw = json.load(f)
    except Exception:
        return None
    if not isinstance(raw, list) or not raw:
        return None
    ts = np.array([int(b[0] // 1000) for b in raw], dtype=np.int64)
    o = np.array([float(b[1]) for b in raw])
    h = np.array([float(b[2]) for b in raw])
    l = np.array([float(b[3]) for b in raw])
    c = np.array([float(b[4]) for b in raw])
    v = np.array([float(b[5]) for b in raw])
    iv = int(np.median(np.diff(ts))) if len(ts) > 1 else TF_SECONDS.get(timeframe, 0)
    return dict(ts=ts, close_ts=ts + iv, o=o, h=h, l=l, c=c, v=v,
                interval=iv, symbol=symbol, timeframe=timeframe, n=len(ts))


def load_funding(symbol: str) -> Optional[Dict[str, np.ndarray]]:
    """8h funding series: ts = fundingTime (settlement), rate = fractional rate."""
    p = os.path.join("market_data", "cache", f"binance_funding_{symbol}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            raw = json.load(f)
    except Exception:
        return None
    rows = raw if isinstance(raw, list) else (raw.get("funding") or raw.get("data") or [])
    if not rows:
        return None
    ts, rate, mark = [], [], []
    for r in rows:
        try:
            t = int(r["fundingTime"]) // 1000
            ts.append(t)
            rate.append(float(r["fundingRate"]))
            mk = r.get("markPrice") or 0.0
            mark.append(float(mk) if mk else np.nan)
        except Exception:
            continue
    if not ts:
        return None
    arr = np.array(ts, dtype=np.int64)
    return dict(ts=arr, close_ts=arr, rate=np.array(rate), mark=np.array(mark),
                symbol=symbol, n=len(arr), interval=8 * 3600)


def resample(base: Dict[str, np.ndarray], tf: str) -> Dict[str, np.ndarray]:
    """Aggregate a lower-timeframe OHLCV dict up to `tf` (causal, bucket=open).

    Bars are bucketed by open time; a bucket is only emitted once its own
    interval has elapsed, so the aggregated bar at index k is closed at
    uniq[k] + secs and may not be read before then.
    """
    secs = TF_SECONDS[tf]
    ts = base["ts"]
    bucket = (ts // secs) * secs
    uniq, inv = np.unique(bucket, return_inverse=True)
    k = len(uniq)
    h = np.full(k, -np.inf); l = np.full(k, np.inf); v = np.zeros(k)
    np.maximum.at(h, inv, base["h"])
    np.minimum.at(l, inv, base["l"])
    np.add.at(v, inv, base["v"])
    first = np.full(k, -1, dtype=int)
    last = np.full(k, -1, dtype=int)
    for i, b in enumerate(inv):
        if first[b] < 0:
            first[b] = i
        last[b] = i
    o = base["o"][first]
    c = base["c"][last]
    return dict(ts=uniq, close_ts=uniq + secs, o=o, h=h, l=l, c=c, v=v,
                interval=secs, timeframe=tf, n=k, symbol=base.get("symbol", ""))


def align_causal(ltf_close_ts: np.ndarray, htf: Dict[str, np.ndarray],
                 field: str = "c") -> np.ndarray:
    """Value of `field` from the last HTF bar whose close_ts <= ltf close_ts.

    The only legal HTF accessor in this platform: at the instant LTF bar i
    closes, an HTF bar is knowable only if it has closed at or before then.
    """
    idx = np.searchsorted(htf["close_ts"], ltf_close_ts, side="right") - 1
    out = np.full(len(ltf_close_ts), np.nan)
    ok = idx >= 0
    out[ok] = htf[field][idx[ok]].astype(float)
    return out


def merged_panel(symbols: Iterable[str], tf: str,
                 min_bars: int = 500) -> Optional[Dict[str, np.ndarray]]:
    """Inner-join symbols on common bar stamps for cross-sectional strategies."""
    per: Dict[str, Dict[str, np.ndarray]] = {}
    for s in symbols:
        d = load_ohlcv(s, tf)
        if d is not None and d["n"] >= min_bars:
            per[s] = d
    if len(per) < 2:
        return None
    common: Optional[np.ndarray] = None
    for d in per.values():
        common = d["ts"] if common is None else np.intersect1d(common, d["ts"])
    if common is None or len(common) < min_bars:
        return None
    syms = sorted(per.keys())
    mats = {k: np.full((len(common), len(syms)), np.nan)
            for k in ("o", "h", "l", "c", "v")}
    for j, s in enumerate(syms):
        d = per[s]
        pos = np.searchsorted(d["ts"], common)
        for k in ("o", "h", "l", "c", "v"):
            mats[k][:, j] = d[k][pos]
    iv = int(np.median(np.diff(common)))
    out = dict(ts=common, close_ts=common + iv, interval=iv,
               symbols=syms, n=len(common))
    out.update(mats)
    return out


def funding_matrix(symbols: Iterable[str],
                   grid_ts: np.ndarray) -> Optional[np.ndarray]:
    """Funding rate per symbol aligned to `grid_ts` (last settled rate <= t).

    Shape (len(grid_ts), len(symbols)); NaN where unavailable.
    """
    cols, syms = [], []
    for s in symbols:
        d = load_funding(s)
        if d is None:
            continue
        idx = np.searchsorted(d["ts"], grid_ts, side="right") - 1
        col = np.full(len(grid_ts), np.nan)
        ok = idx >= 0
        col[ok] = d["rate"][idx[ok]]
        cols.append(col)
        syms.append(s)
    if not cols:
        return None
    return np.column_stack(cols)


def load_tf(symbol: str, tf: str) -> Optional[Dict[str, np.ndarray]]:
    """Load a timeframe, resampling from a cached one when it is not on disk.

    Exact timeframes are preferred (1m..1d are cached). Weekly and monthly
    context clocks are NOT cached, so they are aggregated causally from the
    coarsest available finer timeframe (1d), which maximises the number of
    resulting buckets. `1M` is 30-day buckets, not calendar months — this is
    stated rather than hidden, and it is only ever used as a slow trend context.

    Nothing here invents data: a bucket exists only if real bars fell inside it.
    """
    key = f"{symbol}|{tf}"
    if key in _TF_CACHE:
        return _TF_CACHE[key]
    direct = load_ohlcv(symbol, tf)
    if direct is not None and direct["n"] >= 60:
        _TF_CACHE[key] = direct
        return direct
    secs = TF_SECONDS.get(tf, 0)
    if secs <= 0:
        return None
    finer = [t for t, s in TF_SECONDS.items() if 0 < s < secs]
    finer.sort(key=lambda t: -TF_SECONDS[t])   # coarsest first: longest history
    need = 60 if tf in ("1w", "1M") else 100
    for f in finer:
        base = load_ohlcv(symbol, f)
        if base is None or base["n"] < 200:
            continue
        out = resample(base, tf)
        if out["n"] >= need:
            _TF_CACHE[key] = out
            return out
    return None


def economic_screen_rows(*args, **kwargs):  # pragma: no cover - compat shim
    from .runner import economic_screen_rows as _f
    return _f(*args, **kwargs)


def coverage_report(symbols: Iterable[str] = ASSETS,
                    timeframes: Iterable[str] = ("1m", "5m", "15m", "1h",
                                                 "4h", "1d", "1w")) -> list:
    """Truthful data inventory (bars + span) used to gate every claim."""
    rows = []
    for tf in timeframes:
        for s in symbols:
            d = load_ohlcv(s, tf)
            if d is None:
                rows.append(dict(symbol=s, timeframe=tf, bars=0, days=0.0))
                continue
            days = (d["close_ts"][-1] - d["ts"][0]) / 86400.0
            rows.append(dict(symbol=s, timeframe=tf, bars=d["n"],
                             days=round(days, 1)))
    return rows
