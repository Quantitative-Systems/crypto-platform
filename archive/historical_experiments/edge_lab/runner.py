"""Sweep runner part 2: frozen VAL/OOS verification per stream."""
from __future__ import annotations
from typing import Dict, Any
import numpy as np
from .config import SETS_6, TARGET_R_GRID, ATR_STOP_GRID, MIN_TRADES_DEV
from .data import load_stream
from .indicators import atr
from .families import htf_trend_ctx, _align_context
from .engine import run_stream
from .sweep import PARAM_GRID, MAX_HOLD, _split, _signals


def run_one_stream(asset: str, set_id: str) -> Dict[str, Any]:
    cfg = SETS_6[set_id]
    H = load_stream(asset, cfg["htf"])
    M = load_stream(asset, cfg["mtf"])
    L = load_stream(asset, cfg["ltf"])
    base: Dict[str, Any] = dict(asset=asset, set=set_id, htf=cfg["htf"],
                                mtf=cfg["mtf"], ltf=cfg["ltf"])
    if H is None or M is None or L is None:
        base.update(status="MISSING_DATA")
        return base
    n = int(L["n"])
    if n < 300:
        base.update(status="INSUFFICIENT_DATA", n=n)
        return base
    h_dir = htf_trend_ctx(H["h"], H["l"], H["c"])
    m_dir = htf_trend_ctx(M["h"], M["l"], M["c"])
    h_ctx = _align_context(L["close_ts"], H["close_ts"], h_dir)
    m_ctx = _align_context(L["close_ts"], M["close_ts"], m_dir)
    atr_arr = atr(L["h"], L["l"], L["c"], 14)
    mh = MAX_HOLD[set_id]
    (a0, a1), (b0, b1), (c0, c1) = _split(n)
    best = None
    tried = 0
    for pname, p in PARAM_GRID:
        sL, sS = _signals(pname, p, L, h_ctx, m_ctx)
        for am in ATR_STOP_GRID:
            for tr in TARGET_R_GRID:
                dL = np.zeros(n, dtype=bool)
                dS = np.zeros(n, dtype=bool)
                dL[a0:a1] = sL[a0:a1]
                dS[a0:a1] = sS[a0:a1]
                r = run_stream(dL, dS, L["o"], L["h"], L["l"],
                               L["c"], atr_arr, am, tr, mh)
                tried += 1
                if r.n < MIN_TRADES_DEV:
                    continue
                if best is None or r.expectancy_r > best["dev_exp"]:
                    best = dict(param=pname, params=p, atr_mult=am,
                                target_r=tr, dev_n=r.n, dev_exp=r.expectancy_r,
                                dev_net=r.net_r, dev_wr=r.win_rate,
                                dev_pf=r.profit_factor, dev_dd=r.max_dd_r)
    if best is None:
        base.update(status="NO_DEV_CANDIDATE", tried=tried, n=n)
        return base
    sL, sS = _signals(best["param"], best["params"], L, h_ctx, m_ctx)
    vL = np.zeros(n, dtype=bool)
    vS = np.zeros(n, dtype=bool)
    vL[b0:b1] = sL[b0:b1]
    vS[b0:b1] = sS[b0:b1]
    oL = np.zeros(n, dtype=bool)
    oS = np.zeros(n, dtype=bool)
    oL[c0:c1] = sL[c0:c1]
    oS[c0:c1] = sS[c0:c1]
    rv = run_stream(vL, vS, L["o"], L["h"], L["l"], L["c"],
                    atr_arr, best["atr_mult"], best["target_r"], mh)
    ro = run_stream(oL, oS, L["o"], L["h"], L["l"], L["c"],
                    atr_arr, best["atr_mult"], best["target_r"], mh)
    base.update(status="MEASURED", tried=tried, n=n, best=best,
                val=dict(n=rv.n, net=rv.net_r, exp=rv.expectancy_r,
                         wr=rv.win_rate, pf=rv.profit_factor, dd=rv.max_dd_r),
                oos=dict(n=ro.n, net=ro.net_r, exp=ro.expectancy_r,
                         wr=ro.win_rate, pf=ro.profit_factor, dd=ro.max_dd_r),
                windows=dict(dev=[int(a0), int(a1)], val=[int(b0), int(b1)],
                             oos=[int(c0), int(c1)]))
    return base
