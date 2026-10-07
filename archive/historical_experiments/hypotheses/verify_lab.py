"""QCP lab verifier."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def verify_lab(lab_root=None) -> List[str]:
    from .governance_core import (
        LAB_ROOT as D, REQUIRED_PROVENANCE_FIELDS,
        validate_candidate_id, validate_hypothesis_id,
        validate_test_id)
    lab_root = lab_root or D
    errs: List[str] = []
    seen_c: Dict[str, str] = {}
    seen_t: Dict[str, str] = {}
    for hdir in sorted([p for p in lab_root.glob("H-*") if p.is_dir()]):
        hid = hdir.name
        try:
            validate_hypothesis_id(hid)
        except Exception as e:
            errs.append(str(e))
        if not (hdir / "hypothesis.md").exists():
            errs.append("Missing hypothesis.md: %s." % hid)
        if not (hdir / "candidates.md").exists():
            errs.append("Missing candidates.md: %s." % hid)
        for req in ["observations.md", "positive_evidence.md",
                    "negative_evidence.md"]:
            if not (hdir / "research" / req).exists():
                errs.append("Missing research/%s: %s." % (req, hid))
        croot = hdir / "candidates"
        if not croot.exists():
            errs.append("Missing candidates/: %s." % hid)
            continue
        for cdir in sorted([p for p in croot.glob("*") if p.is_dir()]):
            cid = cdir.name
            try:
                validate_candidate_id(cid)
            except Exception as e:
                errs.append(str(e))
            if cid in seen_c:
                errs.append("Dup candidate %s." % cid)
            else:
                seen_c[cid] = hid
            cfile = cdir / "candidate.md"
            if not cfile.exists():
                errs.append("Missing candidate.md: %s." % cid)
            else:
                t = cfile.read_text(encoding="utf-8")
                if ("- Hypothesis: %s" % hid) not in t:
                    errs.append("Rel mismatch %s/%s." % (hid, cid))
                for req_f in ["- Asset:", "- Timeframe scale:",
                              "- Mechanism:", "- Status:"]:
                    if req_f not in t:
                        errs.append("Missing %s in %s." % (req_f, cid))
            troot = cdir / "tests"
            if not troot.exists():
                errs.append("Missing tests/: %s." % cid)
                continue
            for tdir in sorted([p for p in troot.glob("*") if p.is_dir()]):
                tid = tdir.name
                try:
                    validate_test_id(tid)
                except Exception as e:
                    errs.append(str(e))
                if tid in seen_t:
                    errs.append("Dup test %s." % tid)
                else:
                    seen_t[tid] = hid + "/" + cid
                for req in ["test_plan.md", "config.yaml",
                            "results.json", "report.md"]:
                    if not (tdir / req).exists():
                        errs.append("Missing %s in %s." % (req, tid))
                rjp = tdir / "results.json"
                if rjp.exists():
                    try:
                        data = json.loads(rjp.read_text(encoding="utf-8"))
                    except Exception as e:
                        errs.append("Bad JSON %s." % tid)
                        continue
                    prov = data.get("provenance")
                    terminal = data.get("status") not in (
                        None, "PLANNED", "RUNNING", "COMPLETED")
                    if terminal and prov is None:
                        errs.append("No provenance: %s." % tid)
                    elif isinstance(prov, dict):
                        miss = [f for f in REQUIRED_PROVENANCE_FIELDS
                                if f not in prov or prov[f] in (None, "")]
                        if miss and data.get("status") not in (
                                "PLANNED", "RUNNING"):
                            errs.append("Prov gaps %s." % tid)
                        if (prov.get("hypothesis_id") != hid
                                or prov.get("candidate_id") != cid
                                or prov.get("test_id") != tid):
                            errs.append("Prov mismatch: %s." % tid)
    for hdir in sorted([p for p in lab_root.glob("H-*") if p.is_dir()]):
        neg = hdir / "research" / "negative_evidence.md"
        nt = neg.read_text(encoding="utf-8") if neg.exists() else ""
        for tdir in sorted((hdir / "candidates").glob("*/tests/*")):
            rjp = tdir / "results.json"
            if not rjp.exists():
                continue
            try:
                data = json.loads(rjp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("status") in ("NEGATIVE_SIGNAL", "INVALIDATED"):
                if tdir.name not in nt:
                    errs.append("Neg lost: %s." % tdir.name)
    hp = lab_root / "HYPOTHESES_LIST.md"
    cp = lab_root / "CANDIDATES_LIST.md"
    if hp.exists() and cp.exists():
        ht = hp.read_text(encoding="utf-8")
        ct = cp.read_text(encoding="utf-8")
        for hdir in sorted([p for p in lab_root.glob("H-*") if p.is_dir()]):
            if hdir.name not in ht:
                errs.append("Index miss H: %s." % hdir.name)
        for cid in seen_c:
            if cid not in ct:
                errs.append("Index miss C: %s." % cid)
    else:
        errs.append("Missing global indexes.")
    return errs
