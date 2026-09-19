"""QCP governance ops-A: create hypothesis/candidate."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .governance_core import (
    DuplicateIDError, MissingMetadataError, OrphanTestError,
    candidate_dir, hypothesis_dir, validate_candidate_id,
    validate_hypothesis_id,
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_hypothesis(hid, title, research_question, status="PROPOSED",
                      null_hypothesis="No reliable positive expectancy.",
                      falsification="Net expectancy <= 0 on DEV.",
                      mechanism="", decision="Undecided.", lab_root=None) -> Path:
    from .governance_core import HYPOTHESIS_STATUSES, LAB_ROOT as D
    lab_root = lab_root or D
    validate_hypothesis_id(hid)
    if status not in HYPOTHESIS_STATUSES:
        raise MissingMetadataError("Bad hypothesis status %r." % (status,))
    if not title or not research_question:
        raise MissingMetadataError("Need title + research_question.")
    hdir = hypothesis_dir(hid, lab_root)
    if hdir.exists():
        raise DuplicateIDError("Hypothesis exists: %s." % hid)
    (hdir / "candidates").mkdir(parents=True, exist_ok=False)
    (hdir / "research").mkdir(parents=True, exist_ok=True)
    created = utcnow()
    (hdir / "hypothesis.md").write_text(
        "# %s — %s\n\n## Status\n%s\n\n## Research question\n%s\n\n"
        "## Null hypothesis\n%s\n\n## Falsification criteria\n%s\n\n"
        "## Mechanism summary\n%s\n\n## Decision\n%s\n\n- Created: %s\n"
        % (hid, title, status, research_question, null_hypothesis,
           falsification, mechanism or "(see candidates/)",
           decision, created), encoding="utf-8")
    (hdir / "candidates.md").write_text(
        "# %s — candidates\n\n| candidate | asset | timeframe |"
        " mechanism | status |\n|---|---|---|---|---|\n" % hid,
        encoding="utf-8")
    (hdir / "research" / "observations.md").write_text(
        "# %s — observations\n\n- Created %s.\n" % (hid, created),
        encoding="utf-8")
    (hdir / "research" / "positive_evidence.md").write_text(
        "# %s — positive evidence\n\n(No entries yet.)\n" % hid,
        encoding="utf-8")
    (hdir / "research" / "negative_evidence.md").write_text(
        "# %s — negative evidence\n\n(No entries yet. Preserved.)\n" % hid,
        encoding="utf-8")
    return hdir


def create_candidate(hid, cid, asset, timeframe_scale, mechanism,
                     status="DISCOVERED", lab_root=None) -> Path:
    from .governance_core import CANDIDATE_STATUSES, LAB_ROOT as D
    lab_root = lab_root or D
    validate_candidate_id(cid)
    if status not in CANDIDATE_STATUSES:
        raise MissingMetadataError("Bad candidate status %r." % (status,))
    if not asset or not timeframe_scale or not mechanism:
        raise MissingMetadataError("Need asset/timeframe/mechanism.")
    hdir = hypothesis_dir(hid, lab_root)
    if not hdir.exists():
        raise OrphanTestError("No hypothesis %s." % hid)
    for ex in lab_root.glob("H-*/candidates/*"):
        if ex.name == cid and ex.parent.parent.name != hid:
            raise DuplicateIDError("Candidate %s under %s."
                                   % (cid, ex.parent.parent.name))
    cdir = candidate_dir(hid, cid, lab_root)
    if cdir.exists():
        raise DuplicateIDError("Candidate exists: %s." % cid)
    (cdir / "tests").mkdir(parents=True, exist_ok=False)
    (cdir / "candidate.md").write_text(
        "# %s — %s\n\n- Hypothesis: %s\n- Asset: %s\n"
        "- Timeframe scale: %s\n- Mechanism: %s\n- Status: %s\n"
        "- Created: %s\n" % (cid, mechanism, hid, asset, timeframe_scale,
                             mechanism, status, utcnow()),
        encoding="utf-8")
    return cdir
