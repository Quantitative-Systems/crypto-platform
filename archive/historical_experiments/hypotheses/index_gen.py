"""QCP indexes: generate."""
from __future__ import annotations

import json
import re


def generate_indexes(lab_root=None) -> None:
    from .governance_core import LAB_ROOT as D
    from .index_rows import cand_row, read_status
    lab_root = lab_root or D
    hdirs = sorted([p for p in lab_root.glob("H-*") if p.is_dir()])
    hl = ["# HYPOTHESES_LIST — QCP Research Laboratory", "",
          "Positive DEV result != winner. No VAL/OOS/capital from DEV.",
          "",
          "| ID | title | status | research question | candidates |"
          " latest test | latest evidence | next action |",
          "|---|---|---|---|---|---|---|---|"]
    cl = ["# CANDIDATES_LIST — QCP Research Laboratory", "",
          "| candidate ID | hypothesis ID | asset | timeframe scale |"
          " mechanism | status | latest test | evidence summary |"
          " next action |",
          "|---|---|---|---|---|---|---|---|---|"]
    for hdir in hdirs:
        hid = hdir.name
        hp = hdir / "hypothesis.md"
        ht = hp.read_text(encoding="utf-8") if hp.exists() else ""
        title = ""
        m = re.search(r"^#\s*\S+\s*—\s*(.+?)\s*$", ht, re.M)
        if m:
            title = m.group(1).strip()
        rq = ""
        m2 = re.search(r"^## Research question\s*\n(.+?)(?:\n## |\Z)",
                       ht, re.M | re.S)
        if m2:
            rq = " ".join(m2.group(1).strip().split())[:160]
        st = read_status(hp, "hypothesis") if hp.exists() else "UNKNOWN"
        cdirs = sorted([p for p in (hdir / "candidates").glob("*")
                        if p.is_dir()]) if (
                            hdir / "candidates").exists() else []
        latest = "-"
        lev = "-"
        for cdir in cdirs:
            troot = cdir / "tests"
            if not troot.exists():
                continue
            for tdir in sorted(troot.glob("*")):
                try:
                    r = json.loads((tdir / "results.json").read_text(
                        encoding="utf-8"))
                    latest = r.get("test_id", tdir.name)
                    mm = r.get("metrics") or {}
                    lev = "%s N=%s net=%s" % (
                        r.get("status"), mm.get("total_trades"),
                        mm.get("net_r"))
                except Exception:
                    pass
        nxt = "preserve; VAL/OOS locked"
        if hid == "H-FRACTAL-01":
            nxt = "DO NOT TEST — infrastructure only"
        if st in ("NOT_SUPPORTED", "INVALIDATED", "ARCHIVED"):
            nxt = "preserve; no new testing without governance"
        hl.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            hid, title, st, rq, len(cdirs), latest, lev, nxt))
        rows = []
        for cdir in cdirs:
            r = cand_row(hid, cdir)
            nx = "hold; VAL/OOS locked"
            if r["status"] in ("REJECTED", "INVALIDATED", "ARCHIVED"):
                nx = "preserve negative evidence"
            cl.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                      % (r["cid"], r["hid"], r["asset"], r["tf"],
                         r["mech"], r["status"], r["latest"],
                         r["ev"], nx))
            rows.append("| %s | %s | %s | %s | %s |" % (
                r["cid"], r["asset"], r["tf"], r["mech"], r["status"]))
        (hdir / "candidates.md").write_text(
            "# %s — candidates\n\n| candidate | asset | timeframe |"
            " mechanism | status |\n|---|---|---|---|---|\n%s\n" % (
                hid, "\n".join(rows)), encoding="utf-8")
    (lab_root / "HYPOTHESES_LIST.md").write_text(
        "\n".join(hl) + "\n", encoding="utf-8")
    (lab_root / "CANDIDATES_LIST.md").write_text(
        "\n".join(cl) + "\n", encoding="utf-8")
