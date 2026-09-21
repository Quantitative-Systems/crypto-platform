"""Promotion verdict writer — evaluates all v2 streams, writes paper portfolio.

Writes research/results/edge_lab_v2/promotion.json with per-stream verdicts,
bootstrap stats, and cost-shock expectancy. This is the self-improving ledger:
re-running this file after new data arrives updates verdicts automatically.
"""
from __future__ import annotations
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from research.edge_lab.config import (SETS_6, TAKER_FEE_PCT, SLIPPAGE_PCT,
                                      SPREAD_PCT)
from research.edge_lab.data import load_stream
from research.edge_lab.indicators import atr
from research.edge_lab.families import htf_trend_ctx, _align_context
from research.edge_lab.families_v2 import (v2_breakout_expansion,
                                           v2_trend_expansion,
                                           v2_supertrend_filtered)
from research.edge_lab.sweep import _split
from research.edge_lab.engine import run_stream
from research.edge_lab.promotion import evaluate

HOLD = {"SET_1": 30, "SET_2": 40, "SET_3": 40, "SET_4": 60, "SET_5": 60,
        "SET_6": 80}


def _oos_signals(b, L, h_ctx, m_ctx, aa):
    if b["param"].startswith("V2_BREAK"):
        return v2_breakout_expansion(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, aa, lookback=b["params"].get("lookback", 50))
    if b["param"].startswith("V2_TREND"):
        return v2_trend_expansion(
            L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
            h_ctx, m_ctx, aa)
    return v2_supertrend_filtered(
        L["o"], L["h"], L["l"], L["c"], L["ts"], L["close_ts"],
        h_ctx, m_ctx, aa)


def main() -> int:
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "results", "edge_lab_v2",
        "edge_lab_v2.json")
    rows = json.load(open(src))
    out = []
    for r in rows:
        rec = dict(asset=r["asset"], set=r["set"], status=r.get("status"))
        if r.get("status") != "MEASURED":
            rec.update(verdict="REJECTED",
                       reason=r.get("status"), checks={})
            out.append(rec)
            continue
        b = r["best"]
        cfg = SETS_6[r["set"]]
        H = load_stream(r["asset"], cfg["htf"])
        M = load_stream(r["asset"], cfg["mtf"])
        L = load_stream(r["asset"], cfg["ltf"])
        h_ctx = _align_context(L["close_ts"], H["close_ts"],
                               htf_trend_ctx(H["h"], H["l"], H["c"]))
        m_ctx = _align_context(L["close_ts"], M["close_ts"],
                               htf_trend_ctx(M["h"], M["l"], M["c"]))
        aa = atr(L["h"], L["l"], L["c"], 14)
        n = int(L["n"])
        (a0, a1), (b0, b1), (c0, c1) = _split(n)
        sL, sS = _oos_signals(b, L, h_ctx, m_ctx, aa)
        oL = np.zeros(n, dtype=bool)
        oS = np.zeros(n, dtype=bool)
        oL[c0:c1] = sL[c0:c1]
        oS[c0:c1] = sS[c0:c1]
        mh = HOLD[r["set"]]
        ro = run_stream(oL, oS, L["o"], L["h"], L["l"], L["c"], aa,
                        b["atr_mult"], b["target_r"], mh)
        rsh = run_stream(oL, oS, L["o"], L["h"], L["l"], L["c"], aa,
                         b["atr_mult"], b["target_r"], mh,
                         fee_pct=TAKER_FEE_PCT * 1.5,
                         slip_pct=SLIPPAGE_PCT * 1.5,
                         spread_pct=SPREAD_PCT)
        verdict, checks = evaluate(
            r, ro.realized, rsh.expectancy_r if rsh.n else None)
        rec.update(best=b, val=r["val"], oos=r["oos"],
                   oos_shock_exp=round(float(rsh.expectancy_r), 4)
                   if rsh.n else None,
                   verdict=verdict, checks=checks)
        out.append(rec)
    promo = [x for x in out if x["verdict"] == "PROMOTABLE_PAPER_ONLY"]
    rej = [x for x in out if x["verdict"] == "REJECTED"]
    payload = dict(n_streams=len(out), n_promotable=len(promo),
                   n_rejected=len(rej), rows=out)
    dst = os.path.join(os.path.dirname(src), "promotion.json")
    json.dump(payload, open(dst, "w"), indent=2, default=str)
    print(f"PROMOTABLE ({len(promo)}):")
    for x in promo:
        b = x["best"]
        print("  ", x["asset"], x["set"], b["param"],
              "DEV", round(b["dev_exp"], 3),
              "VAL", round(x["val"]["exp"], 3),
              "OOS", round(x["oos"]["exp"], 3),
              "shock", x["oos_shock_exp"],
              "WFR", x["checks"].get("D4_wfr_value"))
    print(f"REJECTED: {len(rej)} (incl. SET_5/SET_6 cost-blocked)")
    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
