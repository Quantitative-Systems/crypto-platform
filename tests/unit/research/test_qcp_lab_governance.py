"""Structural tests for the QCP research laboratory (qcp/hypotheses).

Proves: creation, ID uniqueness, metadata enforcement, relationship
validity, lifecycle transitions, promotion gates (DEV != winner),
provenance enforcement, negative-evidence preservation, index
synchronization, and integrity of the real migrated lab.
"""
from __future__ import annotations

import json

import pytest

from qcp.hypotheses.governance import (
    LAB_ROOT, DuplicateIDError, InvalidTransitionError, MissingMetadataError,
    MissingProvenanceError, OrphanTestError, UnauthorizedPromotionError,
    create_candidate, create_hypothesis, create_test, promote_candidate,
    record_test_result, transition_candidate, transition_hypothesis,
    transition_test)
from qcp.hypotheses.index_gen import generate_indexes
from qcp.hypotheses.verify_lab import verify_lab

FULL_PROV_FIELDS = [
    "original_path", "experiment_id", "hypothesis_id", "candidate_id",
    "test_id", "strategy_mechanism_version", "data_version",
    "code_commit", "timeframe", "asset", "execution_assumptions",
    "fees", "slippage", "collision_reentry_semantics",
    "result_classification"]


def full_prov(hid, cid, tid):
    p = {f: "x" for f in FULL_PROV_FIELDS}
    p.update({"hypothesis_id": hid, "candidate_id": cid, "test_id": tid})
    return p


def seed(lab):
    create_hypothesis("H-TEST-01", "T", "Q?", lab_root=lab)
    create_candidate("H-TEST-01", "C-TEST-01", "BTC/USDT", "LTF",
                     "mechanism", lab_root=lab)
    create_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01", "BTC/USDT", "1h",
                config={"data_partition": "DEV", "fees": "2/5 bps",
                        "slippage": "5 bps",
                        "execution_assumptions": "adverse-first"},
                lab_root=lab)


def test_hypothesis_creation(tmp_path):
    create_hypothesis("H-TEST-01", "T", "Q?", lab_root=tmp_path)
    d = tmp_path / "H-TEST-01"
    for req in ["hypothesis.md", "candidates.md", "candidates",
                "research/observations.md", "research/positive_evidence.md",
                "research/negative_evidence.md"]:
        assert (d / req).exists(), req


def test_candidate_creation(tmp_path):
    seed(tmp_path)
    d = tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01"
    assert (d / "candidate.md").exists()
    assert (d / "tests").is_dir()
    t = (d / "candidate.md").read_text()
    assert "- Hypothesis: H-TEST-01" in t
    assert "- Asset: BTC/USDT" in t


def test_test_creation(tmp_path):
    seed(tmp_path)
    d = tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01" / "tests" / \
        "T-TEST-01-T01"
    for req in ["test_plan.md", "config.yaml", "results.json", "report.md"]:
        assert (d / req).exists(), req


def test_required_metadata_enforced(tmp_path):
    create_hypothesis("H-TEST-01", "T", "Q?", lab_root=tmp_path)
    with pytest.raises(MissingMetadataError):
        create_candidate("H-TEST-01", "C-TEST-01", "", "LTF", "m",
                         lab_root=tmp_path)
    with pytest.raises(MissingMetadataError):
        create_candidate("H-TEST-01", "C-TEST-01", "BTC", "LTF", "m",
                         status="BOGUS", lab_root=tmp_path)
    create_candidate("H-TEST-01", "C-TEST-01", "BTC", "LTF", "m",
                     lab_root=tmp_path)
    with pytest.raises(MissingMetadataError):
        create_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01", "BTC", "1h",
                    config={"fees": "f"}, lab_root=tmp_path)


def test_duplicate_ids_rejected(tmp_path):
    seed(tmp_path)
    with pytest.raises(DuplicateIDError):
        create_hypothesis("H-TEST-01", "T2", "Q2", lab_root=tmp_path)
    with pytest.raises(DuplicateIDError):
        create_candidate("H-TEST-01", "C-TEST-01", "BTC", "LTF", "m",
                         lab_root=tmp_path)
    with pytest.raises(DuplicateIDError):
        create_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01", "BTC", "1h",
                    config={"data_partition": "D", "fees": "f",
                            "slippage": "s",
                            "execution_assumptions": "a"},
                    lab_root=tmp_path)


def test_orphan_relationships_rejected(tmp_path):
    create_hypothesis("H-TEST-01", "T", "Q?", lab_root=tmp_path)
    with pytest.raises(OrphanTestError):
        create_candidate("H-NOPE-99", "C-TEST-01", "BTC", "LTF", "m",
                         lab_root=tmp_path)
    with pytest.raises(OrphanTestError):
        create_test("H-TEST-01", "C-MISSING", "T-TEST-01-T01", "BTC", "1h",
                    config={"data_partition": "D", "fees": "f",
                            "slippage": "s",
                            "execution_assumptions": "a"},
                    lab_root=tmp_path)


def test_lifecycle_transitions(tmp_path):
    seed(tmp_path)
    transition_hypothesis("H-TEST-01", "FORMALIZED", tmp_path)
    transition_hypothesis("H-TEST-01", "UNDER_RESEARCH", tmp_path)
    with pytest.raises(InvalidTransitionError):
        transition_hypothesis("H-TEST-01", "PROPOSED", tmp_path)
    transition_candidate("H-TEST-01", "C-TEST-01", "UNDER_TEST", tmp_path)
    transition_candidate("H-TEST-01", "C-TEST-01", "PROMISING", tmp_path)
    with pytest.raises(UnauthorizedPromotionError):
        transition_candidate("H-TEST-01", "C-TEST-01", "VALIDATED",
                             tmp_path)
    transition_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01", "RUNNING",
                    tmp_path)
    transition_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01", "COMPLETED",
                    tmp_path)
    transition_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                    "POSITIVE_SIGNAL", tmp_path)
    with pytest.raises(InvalidTransitionError):
        transition_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                        "NEGATIVE_SIGNAL", tmp_path)


def test_positive_dev_cannot_promote(tmp_path):
    seed(tmp_path)
    transition_test("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                    "POSITIVE_SIGNAL", tmp_path)
    cand = (tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01"
            / "candidate.md").read_text()
    assert "- Status: DISCOVERED" in cand  # evidence did not mutate status
    with pytest.raises(UnauthorizedPromotionError):
        transition_candidate("H-TEST-01", "C-TEST-01", "VALIDATED",
                             tmp_path)
    with pytest.raises(UnauthorizedPromotionError):
        promote_candidate("H-TEST-01", "C-TEST-01", "VALIDATED",
                          lab_root=tmp_path)
    with pytest.raises(UnauthorizedPromotionError):
        promote_candidate("H-TEST-01", "C-TEST-01",
                          "VALIDATION_CANDIDATE", authorized=True,
                          lab_root=tmp_path)  # no VAL review evidence


def test_missing_provenance_detected(tmp_path):
    seed(tmp_path)
    bad = full_prov("H-TEST-01", "C-TEST-01", "T-TEST-01-T01")
    del bad["code_commit"]
    with pytest.raises(MissingProvenanceError):
        record_test_result("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                           {"net_r": 1.0}, bad, "POSITIVE_SIGNAL",
                           lab_root=tmp_path)
    with pytest.raises(MissingProvenanceError):
        record_test_result("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                           {"net_r": 1.0}, full_prov("H-O", "C-X", "T-Y"),
                           "POSITIVE_SIGNAL", lab_root=tmp_path)


def test_negative_evidence_preserved(tmp_path):
    seed(tmp_path)
    record_test_result("H-TEST-01", "C-TEST-01", "T-TEST-01-T01",
                       {"total_trades": 8, "net_r": -5.13},
                       full_prov("H-TEST-01", "C-TEST-01",
                                 "T-TEST-01-T01"),
                       "NEGATIVE_SIGNAL", lab_root=tmp_path)
    neg = (tmp_path / "H-TEST-01" / "research"
           / "negative_evidence.md").read_text()
    assert "T-TEST-01-T01" in neg
    results = json.loads(
        (tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01" / "tests"
         / "T-TEST-01-T01" / "results.json").read_text())
    assert results["status"] == "NEGATIVE_SIGNAL"
    # verifier flags lost negative evidence
    negp = (tmp_path / "H-TEST-01" / "research"
            / "negative_evidence.md")
    negp.write_text("(nothing)")
    assert any("Neg lost" in e for e in verify_lab(tmp_path))


def test_verify_lab_detects_missing_provenance_and_orphans(tmp_path):
    seed(tmp_path)
    rj = (tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01" / "tests"
          / "T-TEST-01-T01" / "results.json")
    data = json.loads(rj.read_text())
    data["status"] = "POSITIVE_SIGNAL"  # terminal without provenance
    rj.write_text(json.dumps(data))
    assert any("No provenance" in e for e in verify_lab(tmp_path))
    # orphan test dir (invalid name, no metadata)
    orphan = tmp_path / "H-TEST-01" / "candidates" / "C-TEST-01" / "tests" \
        / "T-ORPHAN-01-T99"
    orphan.mkdir()
    errs = verify_lab(tmp_path)
    assert any("T-ORPHAN-01-T99" in e for e in errs)
    assert any("Missing" in e for e in errs)


def test_indexes_synchronized(tmp_path):
    seed(tmp_path)
    generate_indexes(tmp_path)
    hl = (tmp_path / "HYPOTHESES_LIST.md").read_text()
    cl = (tmp_path / "CANDIDATES_LIST.md").read_text()
    assert "H-TEST-01" in hl
    assert "C-TEST-01" in cl
    create_candidate("H-TEST-01", "C-TEST-02", "ETH/USDT", "LTF", "m2",
                     lab_root=tmp_path)
    generate_indexes(tmp_path)
    assert "C-TEST-02" in (tmp_path / "CANDIDATES_LIST.md").read_text()
    assert verify_lab(tmp_path) == []


def test_real_lab_integrity_and_fractal_lock():
    errs = verify_lab(LAB_ROOT)
    assert errs == [], errs
    hdir = LAB_ROOT / "H-FRACTAL-01"
    assert hdir.exists()
    assert "UNDER_RESEARCH" in (hdir / "hypothesis.md").read_text()
    tests = list((hdir / "candidates").glob("*/tests/*"))
    assert tests == [], "H-FRACTAL-01 must have no tests yet (DO NOT TEST)"
