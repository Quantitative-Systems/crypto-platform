"""QCP indexes: row helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict


def read_status(path: Path, kind: str) -> str:
    t = path.read_text(encoding="utf-8")
    if kind == "hypothesis":
        m = re.search(r"^## Status\s*\n(.+?)\s*$", t, re.M)
    else:
        m = re.search(r"^- Status:\s*(.+?)\s*$", t, re.M)
    return m.group(1).strip() if m else "UNKNOWN"


def cand_row(hid: str, cdir: Path) -> Dict:
    t = (cdir / "candidate.md").read_text(encoding="utf-8")

    def _f(label):
        m = re.search(r"^- " + re.escape(label) + r":\s*(.+?)\s*$", t, re.M)
        return m.group(1).strip() if m else ""

    tests = sorted([p.name for p in (cdir / "tests").glob("*")
                    if p.is_dir()]) if (cdir / "tests").exists() else []
    latest = tests[-1] if tests else "-"
    ev = "-"
    if tests:
        try:
            r = json.loads((cdir / "tests" / latest / "results.json"
                            ).read_text(encoding="utf-8"))
            mm = r.get("metrics") or {}
            ev = "%s N=%s net=%s" % (r.get("status"),
                                     mm.get("total_trades"),
                                     mm.get("net_r"))
        except Exception:
            ev = "unreadable"
    return {"cid": cdir.name, "hid": hid, "asset": _f("Asset"),
            "tf": _f("Timeframe scale"), "mech": _f("Mechanism"),
            "status": _f("Status"), "latest": latest, "ev": ev}
