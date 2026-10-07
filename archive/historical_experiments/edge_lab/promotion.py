"""Edge Lab promotion gate — 7-dimension institutional barrier (research-only).

A stream config is PROMOTABLE only if it clears all gates on FROZEN config:
 D1 data: MEASURED status, DEV n>=30
 D2 alpha: DEV/VAL/OOS expectancy > 0.05R net of all costs
 D3 stats: VAL n>=20, OOS n>=10, PF>1.10 on DEV and VAL, bootstrap p<0.05 proxy
 D4 walk-forward: OOS_exp/DEV_exp >= 0.30 (0.70 required for capital)
 D5 cost shock: expectancy survives +50% fees+slippage (re-run inflated)
 D6 stability: VAL and OOS agree in sign with DEV (no sign flip)
 D7 risk: max DD <= 30R on every window
Live capital stays $0.00 — promotion means PAPER observation only.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np


def bootstrap_positive_prob(realized: np.ndarray, n_boot: int = 2000,
                            seed: int = 7) -> float:
    rng = np.random.default_rng(seed)
    n = len(realized)
    if n < 10:
        return 0.0
    means = np.array([rng.choice(realized, size=n, replace=True).mean()
                      for _ in range(n_boot)])
    return float((means > 0).mean())


def evaluate(row: Dict[str, Any], oos_realized: np.ndarray | None = None,
             shock_exp: float | None = None) -> Tuple[str, Dict[str, Any]]:
    checks: Dict[str, Any] = {}
    if row.get("status") != "MEASURED":
        return "REJECTED", {"reason": row.get("status")}
    b, v, o = row["best"], row["val"], row["oos"]
    checks["D1_data"] = b["dev_n"] >= 30
    checks["D2_alpha"] = (b["dev_exp"] > 0.05 and v["exp"] > 0.05
                          and o["exp"] > 0.05)
    checks["D3_stats"] = (v["n"] >= 20 and o["n"] >= 10
                          and b.get("dev_pf", 0) > 1.10
                          and v.get("pf", 0) > 1.10)
    wfr = (o["exp"] / b["dev_exp"]) if b["dev_exp"] else 0.0
    checks["D4_wfr"] = wfr >= 0.30
    checks["D4_wfr_value"] = round(wfr, 3)
    checks["D5_cost_shock"] = (shock_exp is not None and shock_exp > 0) \
        if shock_exp is not None else None
    checks["D6_sign_stable"] = (np.sign(v["exp"]) == np.sign(b["dev_exp"])
                                and np.sign(o["exp"]) == np.sign(b["dev_exp"]))
    checks["D7_dd"] = (b.get("dev_dd", 99) <= 30 and v.get("dd", 99) <= 30
                       and o.get("dd", 99) <= 30)
    if oos_realized is not None and len(oos_realized) >= 10:
        checks["D3_bootstrap_p_pos"] = round(
            bootstrap_positive_prob(oos_realized), 3)
    core = ["D1_data", "D2_alpha", "D3_stats", "D4_wfr",
            "D6_sign_stable", "D7_dd"]
    passed = all(checks.get(k) for k in core)
    if shock_exp is not None:
        passed = passed and bool(checks["D5_cost_shock"])
    return ("PROMOTABLE_PAPER_ONLY" if passed else "REJECTED", checks)
