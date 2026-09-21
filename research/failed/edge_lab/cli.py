"""Edge Lab CLI: sweep all 60 streams, write ledgers, print verdict table."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
from research.edge_lab.config import ASSETS_10, SETS_6
from research.edge_lab.runner import run_one_stream


def main() -> int:
    out_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), "results", "edge_lab_v1")
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for asset in ASSETS_10:
        for set_id in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5", "SET_6"]:
            print(f"[{asset} {set_id}] ...", flush=True)
            r = run_one_stream(asset, set_id)
            rows.append(r)
            st = r.get("status")
            if st == "MEASURED":
                b = r["best"]
                print(f"  DEV {b['param']} atr={b['atr_mult']} tgt={b['target_r']} "
                      f"n={b['dev_n']} exp={b['dev_exp']:+.4f}R | "
                      f"VAL n={r['val']['n']} exp={r['val']['exp']:+.4f}R | "
                      f"OOS n={r['oos']['n']} exp={r['oos']['exp']:+.4f}R")
            else:
                print(f"  {st}")
    payload = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
                   n_streams=len(rows), rows=rows)
    with open(os.path.join(out_dir, "edge_lab_v1.json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)
    # CSV summary
    import csv
    with open(os.path.join(out_dir, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset", "set", "status", "param", "atr", "tgt",
                    "dev_n", "dev_exp", "val_n", "val_exp",
                    "oos_n", "oos_exp"])
        for r in rows:
            b = r.get("best", {})
            v = r.get("val", {})
            o = r.get("oos", {})
            w.writerow([r["asset"], r["set"], r.get("status"),
                        b.get("param", ""), b.get("atr_mult", ""),
                        b.get("target_r", ""), b.get("dev_n", ""),
                        round(float(b.get("dev_exp", 0) or 0), 4),
                        v.get("n", ""), round(float(v.get("exp", 0) or 0), 4),
                        o.get("n", ""), round(float(o.get("exp", 0) or 0), 4)])
    print(f"\nWrote {out_dir}/edge_lab_v1.json + summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
