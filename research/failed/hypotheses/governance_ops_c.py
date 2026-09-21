"""QCP governance ops-C: transitions + authorized promotion + indexes."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .governance_core import (
    AUTHORIZED_PROMOTION_EDGES, CANDIDATE_TRANSITIONS,
    HYPOTHESIS_TRANSITIONS, InvalidTransitionError,
    MissingMetadataError, TEST_TRANSITIONS,
    UnauthorizedPromotionError, candidate_dir, hypothesis_dir,
    test_dir, validate_transition,
)


def transition_hypothesis(hid, target, lab_root=None) -> None:
    from .governance_core import LAB_ROOT as D
    lab_root = lab_root or D
    md = hypothesis_dir(hid, lab_root) / "hypothesis.md"
    text = md.read_text(encoding="utf-8")
    m = re.search(r"^## Status\s*\n(.+?)\s*$", text, re.M)
    if not m:
        raise MissingMetadataError("Missing ## Status.")
    cur = m.group(1).strip()
    validate_transition(cur, target, HYPOTHESIS_TRANSITIONS, "hypothesis")
    md.write_text(text.replace("## Status\n" + cur, "## Status\n" + target, 1),
                  encoding="utf-8")


def transition_candidate(hid, cid, target, lab_root=None) -> None:
    from .governance_core import LAB_ROOT as D
    lab_root = lab_root or D
    if target in ("VALIDATION_CANDIDATE", "VALIDATED"):
        raise UnauthorizedPromotionError("Use promote_candidate authorized.")
    md = candidate_dir(hid, cid, lab_root) / "candidate.md"
    text = md.read_text(encoding="utf-8")
    m = re.search(r"^- Status:\s*(.+?)\s*$", text, re.M)
    if not m:
        raise MissingMetadataError("Missing - Status.")
    cur = m.group(1).strip()
    validate_transition(cur, target, CANDIDATE_TRANSITIONS, "candidate")
    md.write_text(text.replace("- Status: " + cur, "- Status: " + target, 1),
                  encoding="utf-8")


def promote_candidate(hid, cid, target, authorized=False,
                      validation_evidence=None, lab_root=None) -> None:
    from .governance_core import LAB_ROOT as D
    lab_root = lab_root or D
    if target not in ("VALIDATION_CANDIDATE", "VALIDATED"):
        raise InvalidTransitionError("Only validation states.")
    if not authorized:
        raise UnauthorizedPromotionError("Need authorized=True.")
    if not validation_evidence or not validation_evidence.get(
            "validation_partition_reviewed"):
        raise UnauthorizedPromotionError("Need VAL review evidence.")
    md = candidate_dir(hid, cid, lab_root) / "candidate.md"
    text = md.read_text(encoding="utf-8")
    m = re.search(r"^- Status:\s*(.+?)\s*$", text, re.M)
    cur = m.group(1).strip()
    if (cur, target) not in AUTHORIZED_PROMOTION_EDGES:
        raise InvalidTransitionError("Bad promotion edge %r->%r." % (
            cur, target))
    md.write_text(text.replace("- Status: " + cur, "- Status: " + target, 1),
                  encoding="utf-8")


def transition_test(hid, cid, tid, target, lab_root=None) -> None:
    from .governance_core import LAB_ROOT as D
    lab_root = lab_root or D
    plan = test_dir(hid, cid, tid, lab_root) / "test_plan.md"
    text = plan.read_text(encoding="utf-8")
    m = re.search(r"^- Status:\s*(.+?)\s*$", text, re.M)
    cur = m.group(1).strip()
    eff = dict(TEST_TRANSITIONS)
    eff["PLANNED"] = list(eff["PLANNED"]) + [
        "COMPLETED", "POSITIVE_SIGNAL", "NEGATIVE_SIGNAL",
        "MIXED", "INCONCLUSIVE"]
    eff["RUNNING"] = list(eff["RUNNING"]) + [
        "POSITIVE_SIGNAL", "NEGATIVE_SIGNAL", "MIXED", "INCONCLUSIVE"]
    validate_transition(cur, target, eff, "test")
    plan.write_text(
        text.replace("- Status: " + cur, "- Status: " + target, 1),
        encoding="utf-8")
    rj = test_dir(hid, cid, tid, lab_root) / "results.json"
    try:
        data = json.loads(rj.read_text(encoding="utf-8"))
        data["status"] = target
        rj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
