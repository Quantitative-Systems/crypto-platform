"""QCP governance ops-B: create_test + record_test_result (no promotion)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .governance_core import (
    DuplicateIDError, MissingMetadataError, MissingProvenanceError,
    OrphanTestError, REQUIRED_PROVENANCE_FIELDS,
    REQUIRED_TEST_CONFIG_FIELDS, candidate_dir, hypothesis_dir,
    test_dir, validate_test_id,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_test(hid, cid, tid, asset, timeframe, config=None,
                status="PLANNED", lab_root=None) -> Path:
    from .governance_core import LAB_ROOT as D, TEST_STATUSES
    lab_root = lab_root or D
    validate_test_id(tid)
    if status not in TEST_STATUSES:
        raise MissingMetadataError("Bad test status %r." % (status,))
    cdir = candidate_dir(hid, cid, lab_root)
    if not cdir.exists():
        raise OrphanTestError("No candidate %s/%s." % (hid, cid))
    for ex in lab_root.glob("H-*/candidates/*/tests/*"):
        if ex.name == tid and ex.parent.parent.name != cid:
            raise DuplicateIDError("Test %s exists at %s." % (tid, ex))
    tdir = test_dir(hid, cid, tid, lab_root)
    if tdir.exists():
        raise DuplicateIDError("Test exists: %s." % tid)
    tdir.mkdir(parents=True, exist_ok=False)
    cfg = dict(config or {})
    cfg.setdefault("asset", asset)
    cfg.setdefault("timeframe", timeframe)
    cfg.setdefault("hypothesis_id", hid)
    cfg.setdefault("candidate_id", cid)
    cfg.setdefault("test_id", tid)
    for f in REQUIRED_TEST_CONFIG_FIELDS:
        if f not in cfg or cfg[f] in (None, ""):
            shutil.rmtree(tdir)
            raise MissingMetadataError("Missing config field: %s." % f)
    import yaml as _yaml
    (tdir / "test_plan.md").write_text(
        "# %s — test plan\n\n- Hypothesis: %s\n- Candidate: %s\n"
        "- Status: %s\n- Asset: %s\n- Timeframe: %s\n" % (
            tid, hid, cid, status, asset, timeframe),
        encoding="utf-8")
    (tdir / "config.yaml").write_text(
        _yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    (tdir / "results.json").write_text(json.dumps(
        {"test_id": tid, "candidate_id": cid, "hypothesis_id": hid,
         "status": status, "provenance": None, "metrics": None,
         "note": "Not yet recorded."}, indent=2), encoding="utf-8")
    (tdir / "report.md").write_text(
        "# %s — report\n\nStatus: %s. Not yet recorded.\n" % (tid, status),
        encoding="utf-8")
    return tdir


def record_test_result(hid, cid, tid, metrics, provenance,
                       classification, lab_root=None) -> Path:
    """Record evidence. NEVER mutates candidate/hypothesis status."""
    from .governance_core import LAB_ROOT as D
    lab_root = lab_root or D
    allowed = ["POSITIVE_SIGNAL", "NEGATIVE_SIGNAL", "MIXED",
               "INCONCLUSIVE", "INVALIDATED"]
    if classification not in allowed:
        raise MissingMetadataError("Bad classification %r." % (
            classification,))
    tdir = test_dir(hid, cid, tid, lab_root)
    if not tdir.exists():
        raise OrphanTestError("No test dir: %s." % tdir)
    miss = [f for f in REQUIRED_PROVENANCE_FIELDS
            if f not in provenance or provenance[f] in (None, "")]
    if miss:
        raise MissingProvenanceError("Missing provenance: %s." % (miss,))
    if (provenance.get("hypothesis_id") != hid
            or provenance.get("candidate_id") != cid
            or provenance.get("test_id") != tid):
        raise MissingProvenanceError("Provenance IDs mismatch path.")
    cdir = candidate_dir(hid, cid, lab_root)
    before = (cdir / "candidate.md").read_text(encoding="utf-8")
    payload = {
        "test_id": tid, "candidate_id": cid, "hypothesis_id": hid,
        "status": classification, "metrics": metrics,
        "provenance": provenance, "recorded_at_utc": _utcnow(),
        "promotion_note": "POSITIVE DEV RESULT IS NOT A WINNER. No promotion.",
    }
    (tdir / "results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    (tdir / "report.md").write_text(
        "# %s — report\n\n- Classification: %s\n- Net R: %s | N: %s\n"
        "- Original: %s\n- Experiment: %s\n- Commit: %s\n"
        "- Promotion: NONE.\n" % (
            tid, classification, (metrics or {}).get("net_r"),
            (metrics or {}).get("total_trades"),
            provenance.get("original_path"),
            provenance.get("experiment_id"),
            provenance.get("code_commit")),
        encoding="utf-8")
    after = (cdir / "candidate.md").read_text(encoding="utf-8")
    assert before == after, "record must not mutate candidate"
    hdir = hypothesis_dir(hid, lab_root)
    line = "\n- %s %s %s N=%s net=%s src=%s\n" % (
        _utcnow(), tid, classification, (metrics or {}).get("total_trades"),
        (metrics or {}).get("net_r"), provenance.get("original_path"))
    if classification == "POSITIVE_SIGNAL":
        p = hdir / "research" / "positive_evidence.md"
    elif classification in ("NEGATIVE_SIGNAL", "INVALIDATED"):
        p = hdir / "research" / "negative_evidence.md"
    else:
        p = hdir / "research" / "observations.md"
    with open(p, "a", encoding="utf-8") as f:
        f.write(line)
    return tdir
