"""V2 runner: cost floor + sparse signals + frozen VAL/OOS."""
from __future__ import annotations
from typing import Dict, Any
import numpy as np
from .config import SETS_6, TARGET_R_GRID, ATR_STOP_GRID, MIN_TRADES_DEV
from .data import load_stream
from .indicators import atr
from .families import htf_trend_ctx, _align_context
from .families_v2 import v2_breakout_expansion, v2_trend_expansion, v2_supertrend_filtered
from .filters import MIN_STOP_BPS
from .engine import run_stream
from .sweep import _split

V2_GRID = [
    ("V2_BREAK50", dict(kind="break", lookback=50)),
    ("V2_BREAK20", dict(kind="break", lookback=20)),
    ("V2_TREND", dict(kind="trend")),
    ("V2_SUPER", dict(kind="super")),
]
V2_HOLD = {"SET_1": 30, "SET_2": 40, "SET_3": 40, "SET_4": 60, "SET_5": 60, "SET_6": 80}


def _v2_signals(pname, p, L, h_ctx, m_ctx, atr_arr):
    if p["kind"] == "break":
        return v2_breakout_expansion(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, atr_arr, lookback=p.get("lookback", 50))
    if p["kind"] == "trend":
        return v2_trend_expansion(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, atr_arr)
    return v2_supertrend_filtered(
        L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
        h_ctx, m_ctx, atr_arr)


def run_one_stream_v2(asset: str, set_id: str) -> Dict[str, Any]:
    cfg = SETS_6[set_id]
    H = load_stream(asset, cfg["htf"])
    M = load_stream(asset, cfg["mtf"])
    L = load_stream(asset, cfg["ltf"])
    base: Dict[str, Any] = dict(asset=asset, set=set_id)
    if H is None or M is None or L is None:
        base.update(status="MISSING_DATA")
        return base
    n = int(L["n"])
    if n < 300:
        base.update(status="INSUFFICIENT_DATA", n=n)
        return base
    h_ctx = _align_context(L["close_ts"], H["close_ts"],
                           htf_trend_ctx(H["h"], H["l"], H["c"]))
    m_ctx = _align_context(L["close_ts"], M["close_ts"],
                           htf_trend_ctx(M["h"], M["l"], M["c"]))
    atr_arr = atr(L["h"], L["l"], L["c"], 14)
    mh = V2_HOLD[set_id]
    floor_bps = MIN_STOP_BPS[set_id]
    (a0, a1), (b0, b1), (c0, c1) = _split(n)
    best = None
    tried = 0
    skipped_cost = 0
    for pname, p in V2_GRID:
        sL, sS = _v2_signals(pname, p, L, h_ctx, m_ctx, atr_arr)
        for am in ATR_STOP_GRID:
            for tr in TARGET_R_GRID:
                # cost floor: median DEV stop must clear floor; else skip combo
                dev_sl_bps = np.median(
                    atr_arr[a0:a1] * am / L["c"][a0:a1] * 10000.0)
                if dev_sl_bps < floor_bps:
                    skipped_cost += 1
                    continue
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
        base.update(status="NO_DEV_CANDIDATE", tried=tried,
                    skipped_cost=skipped_cost, n=n)
        return base
    sL, sS = _v2_signals(best["param"], best["params"], L, h_ctx, m_ctx, atr_arr)
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
    base.update(status="MEASURED", tried=tried,
                skipped_cost=skipped_cost, n=n, best=best,
                val=dict(n=rv.n, net=rv.net_r, exp=rv.expectancy_r,
                         wr=rv.win_rate, pf=rv.profit_factor, dd=rv.max_dd_r),
                oos=dict(n=ro.n, net=ro.net_r, exp=ro.expectancy_r,
                         wr=ro.win_rate, pf=ro.profit_factor, dd=ro.max_dd_r))
    return base
