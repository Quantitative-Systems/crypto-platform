"""Data loader for edge lab — reads local cache, returns numpy OHLC + ts."""
from __future__ import annotations
import json
import os
from typing import Optional, Dict, Any
import numpy as np
from market_data.data_manager import DataManager


def load_stream(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    try:
        fpath = DataManager.get_cache_filepath(symbol, timeframe)
    except Exception:
        return None
    if not os.path.exists(fpath):
        return None
    try:
        with open(fpath) as f:
            raw = json.load(f)
    except Exception:
        return None
    if not raw or not isinstance(raw, list):
        return None
    ts = np.array([int(b[0] // 1000) for b in raw], dtype=np.int64)
    o = np.array([float(b[1]) for b in raw])
    h = np.array([float(b[2]) for b in raw])
    lo = np.array([float(b[3]) for b in raw])
    c = np.array([float(b[4]) for b in raw])
    v = np.array([float(b[5]) for b in raw])
    iv = int(ts[1] - ts[0]) if len(ts) > 1 else 0
    close_ts = ts + iv
    return dict(ts=ts, o=o, h=h, l=lo, c=c, v=v,
                interval=iv, close_ts=close_ts, n=len(ts))
