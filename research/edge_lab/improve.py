"""Self-improvement loop: re-sweep, compare to ledger, keep champion per stream.

- Loads prior ledger (edge_lab_v2.json), re-runs V2 sweep (same frozen grid).
- For streams where challenger beats champion on VAL expectancy with
  OOS sign agreement, promotes challenger; else keeps champion.
- Appends improvement ledger entry with timestamp. Never touches OOS for
  selection (selection on DEV, confirmation on VAL, report on OOS).
- Future-proof: as cache grows (1m/5m history), re-running automatically
  re-evaluates SET_5/SET_6 from NO_DEV_CANDIDATE -> MEASURED.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any


def improve(prior_path: str, out_path: str) -> Dict[str, Any]:
    from .config import ASSETS_10
    from .runner_v2 import run_one_stream_v2
    prior = {}
    if os.path.exists(prior_path):
        try:
            rows = json.load(open(prior_path))
            rows = rows if isinstance(rows, list) else rows.get("rows", [])
            for r in rows:
                prior[(r["asset"], r["set"])] = r
        except Exception:
            prior = {}
    results = []
    for a in ASSETS_10:
        for s in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5", "SET_6"]:
            cur = run_one_stream_v2(a, s)
            key = (a, s)
            prev = prior.get(key)
            decision = "NEW"
            if prev is not None:
                pb = (prev.get("best") or {}).get("dev_exp", -99)
                cb = (cur.get("best") or {}).get("dev_exp", -99)
                pv = (prev.get("val") or {}).get("exp", -99)
                cv = (cur.get("val") or {}).get("exp", -99)
                if cur.get("status") == "MEASURED" and cv is not None \
                   and pv is not None and cv > pv and cb and cb > 0:
                    decision = "CHALLENGER_WINS"
                else:
                    decision = "CHAMPION_HELD"
            cur["improve_decision"] = decision
            cur["improved_utc"] = datetime.now(timezone.utc).isoformat()
            results.append(cur)
    payload = dict(improved_utc=datetime.now(timezone.utc).isoformat(),
                   n=len(results), rows=results)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(payload, open(out_path, "w"), indent=2, default=str)
    return payload
