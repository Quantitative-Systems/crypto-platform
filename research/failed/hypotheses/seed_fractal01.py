"""Seed H-FRACTAL-01 shell (infrastructure only, no tests run)."""
from pathlib import Path
from .governance_ops_a import create_hypothesis

LAB = Path(__file__).resolve().parent

DEF = {
    "hid": "H-FRACTAL-01",
    "title": "Cross-Scale Mechanism Transfer",
    "research_question": (
        "If a mechanism shows DEV evidence at one timeframe scale, "
        "does it retain measurable economic behavior at other scales/assets?"),
    "status": "UNDER_RESEARCH",
    "null_hypothesis": (
        "Performance at one scale provides no reliable evidence of "
        "positive expectancy at another scale/asset."),
    "falsification": (
        "DEV expectancy <= 0.0R and PF <= 1.0 at every other tested scale; "
        "no cross-scale correlation above chance."),
    "mechanism": (
        "A valid market mechanism may exhibit partial transfer across "
        "timeframe scales/assets; must be demonstrated empirically."),
    "decision": "Infrastructure registered. DO NOT TEST yet.",
}


def ensure() -> Path:
    hdir = LAB / "H-FRACTAL-01"
    if hdir.exists():
        # repair/complete skeleton idempotently (infrastructure only)
        (hdir / "candidates").mkdir(exist_ok=True)
        res = hdir / "research"
        res.mkdir(exist_ok=True)
        for f in ("observations.md", "positive_evidence.md",
                  "negative_evidence.md"):
            p = res / f
            if not p.exists():
                p.write_text(f"# {f.replace('_', ' ').title()}\n\n"
                             "(no entries yet)\n", encoding="utf-8")
        if not (hdir / "candidates.md").exists():
            (hdir / "candidates.md").write_text(
                "# Candidates — H-FRACTAL-01\n\n"
                "(no candidates registered yet)\n", encoding="utf-8")
        # enforce status UNDER_RESEARCH minimum
        from .governance_ops_c import transition_hypothesis
        from .index_rows import read_status
        cur = read_status(hdir / "hypothesis.md", "hypothesis")
        if cur == "PROPOSED":
            transition_hypothesis("H-FRACTAL-01", "FORMALIZED", LAB)
            transition_hypothesis("H-FRACTAL-01", "UNDER_RESEARCH", LAB)
        elif cur == "FORMALIZED":
            transition_hypothesis("H-FRACTAL-01", "UNDER_RESEARCH", LAB)
        return hdir
    return create_hypothesis(lab_root=LAB, **DEF)
