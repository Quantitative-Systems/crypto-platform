"""
QCP Research Laboratory — governance part 1: constants, exceptions, validators.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LAB_ROOT = Path(__file__).resolve().parent
HYPOTHESES_LIST = LAB_ROOT / "HYPOTHESES_LIST.md"
CANDIDATES_LIST = LAB_ROOT / "CANDIDATES_LIST.md"

HYPOTHESIS_ID_PATTERN = re.compile(r"^H-[A-Z]{2,20}-\d{2}$")
CANDIDATE_ID_PATTERN = re.compile(r"^C-[A-Z]{2,20}-\d{2}[A-Z]?$")
TEST_ID_PATTERN = re.compile(r"^T-[A-Z]{2,20}-\d{2}[A-Z]?-T\d{2}$")

HYPOTHESIS_STATUSES = [
    "PROPOSED", "FORMALIZED", "UNDER_RESEARCH", "ACTIVE",
    "SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED",
    "INVALIDATED", "ARCHIVED",
]
CANDIDATE_STATUSES = [
    "DISCOVERED", "UNDER_TEST", "PROMISING",
    "VALIDATION_CANDIDATE", "VALIDATED",
    "REJECTED", "INVALIDATED", "ARCHIVED",
]
TEST_STATUSES = [
    "PLANNED", "RUNNING", "COMPLETED",
    "POSITIVE_SIGNAL", "NEGATIVE_SIGNAL", "MIXED",
    "INCONCLUSIVE", "INVALIDATED",
]
HYPOTHESIS_TRANSITIONS: Dict[str, List[str]] = {
    "PROPOSED": ["FORMALIZED", "ARCHIVED"],
    "FORMALIZED": ["UNDER_RESEARCH", "ACTIVE", "ARCHIVED"],
    "UNDER_RESEARCH": ["ACTIVE", "SUPPORTED", "PARTIALLY_SUPPORTED",
                       "NOT_SUPPORTED", "INVALIDATED", "ARCHIVED"],
    "ACTIVE": ["UNDER_RESEARCH", "SUPPORTED", "PARTIALLY_SUPPORTED",
               "NOT_SUPPORTED", "INVALIDATED", "ARCHIVED"],
    "SUPPORTED": ["ARCHIVED"],
    "PARTIALLY_SUPPORTED": ["ACTIVE", "UNDER_RESEARCH", "ARCHIVED"],
    "NOT_SUPPORTED": ["ARCHIVED"],
    "INVALIDATED": ["ARCHIVED"],
    "ARCHIVED": [],
}
# UNDER_TEST/PROMISING NEVER go directly to VALIDATION_CANDIDATE/VALIDATED.
CANDIDATE_TRANSITIONS: Dict[str, List[str]] = {
    "DISCOVERED": ["UNDER_TEST", "REJECTED", "ARCHIVED"],
    "UNDER_TEST": ["PROMISING", "REJECTED", "INVALIDATED", "ARCHIVED"],
    "PROMISING": ["UNDER_TEST", "REJECTED", "INVALIDATED", "ARCHIVED"],
    "VALIDATION_CANDIDATE": ["VALIDATED", "REJECTED", "INVALIDATED", "ARCHIVED"],
    "VALIDATED": ["ARCHIVED"],
    "REJECTED": ["ARCHIVED"],
    "INVALIDATED": ["ARCHIVED"],
    "ARCHIVED": [],
}
AUTHORIZED_PROMOTION_EDGES = {
    ("PROMISING", "VALIDATION_CANDIDATE"),
    ("UNDER_TEST", "VALIDATION_CANDIDATE"),
    ("VALIDATION_CANDIDATE", "VALIDATED"),
}
TEST_TRANSITIONS: Dict[str, List[str]] = {
    "PLANNED": ["RUNNING", "INVALIDATED"],
    "RUNNING": ["COMPLETED", "INVALIDATED"],
    "COMPLETED": ["POSITIVE_SIGNAL", "NEGATIVE_SIGNAL", "MIXED",
                  "INCONCLUSIVE", "INVALIDATED"],
    "POSITIVE_SIGNAL": [], "NEGATIVE_SIGNAL": [], "MIXED": [],
    "INCONCLUSIVE": [], "INVALIDATED": [],
}
REQUIRED_PROVENANCE_FIELDS = [
    "original_path", "experiment_id", "hypothesis_id", "candidate_id",
    "test_id", "strategy_mechanism_version", "data_version", "code_commit",
    "timeframe", "asset", "execution_assumptions", "fees", "slippage",
    "collision_reentry_semantics", "result_classification",
]
REQUIRED_TEST_CONFIG_FIELDS = [
    "asset", "timeframe", "fees", "slippage",
    "data_partition", "execution_assumptions",
]


class LabError(Exception):
    pass


class DuplicateIDError(LabError):
    pass


class InvalidIDError(LabError):
    pass


class InvalidTransitionError(LabError):
    pass


class MissingMetadataError(LabError):
    pass


class MissingProvenanceError(LabError):
    pass


class OrphanTestError(LabError):
    pass


class UnauthorizedPromotionError(LabError):
    pass


def validate_hypothesis_id(hid: str) -> None:
    if not HYPOTHESIS_ID_PATTERN.match(hid or ""):
        raise InvalidIDError(
            "Invalid hypothesis ID %r. Expected H-<FAMILY>-<NN>." % (hid,))


def validate_candidate_id(cid: str) -> None:
    if not CANDIDATE_ID_PATTERN.match(cid or ""):
        raise InvalidIDError(
            "Invalid candidate ID %r. Expected C-<FAMILY>-<NN>[A-Z]." % (cid,))


def validate_test_id(tid: str) -> None:
    if not TEST_ID_PATTERN.match(tid or ""):
        raise InvalidIDError(
            "Invalid test ID %r. Expected T-<FAMILY>-<NN>[A-Z]-T<NN>."
            % (tid,))


def validate_transition(
    current: str, target: str, table: Dict[str, List[str]], kind: str
) -> None:
    if current not in table:
        raise InvalidTransitionError("Unknown %s status %r." % (kind, current))
    if target not in table[current]:
        raise InvalidTransitionError(
            "Invalid %s transition %r -> %r. Allowed: %s."
            % (kind, current, target, table[current]))


def hypothesis_dir(hid: str, lab_root: Path = LAB_ROOT) -> Path:
    return lab_root / hid


def candidate_dir(hid: str, cid: str, lab_root: Path = LAB_ROOT) -> Path:
    return lab_root / hid / "candidates" / cid


def test_dir(hid: str, cid: str, tid: str, lab_root: Path = LAB_ROOT) -> Path:
    return lab_root / hid / "candidates" / cid / "tests" / tid
