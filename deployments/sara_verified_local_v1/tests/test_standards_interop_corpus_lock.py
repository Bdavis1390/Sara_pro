from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.qualification import canonical_digest


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.json"
LOCK_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.lock.json"


def test_frozen_corpus_matches_canonical_digest_and_case_inventory():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    assert canonical_digest(corpus) == lock["canonical_sha256"]
    assert corpus["schema"] == lock["corpus_schema"]
    assert corpus["ocsf_target"] == lock["ocsf_target"]
    assert corpus["gemara_target"] == lock["gemara_target"]
    assert corpus["external_validation_status"] == "NOT_RUN"
    assert lock["external_validation_status"] == "NOT_RUN"

    case_ids = [case["case_id"] for case in corpus["cases"]]
    assert len(case_ids) == lock["case_count"]
    assert case_ids == lock["case_ids"]


def test_v0_1_lock_requires_versioned_change_instead_of_silent_fixture_mutation():
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    assert lock["internal_freeze_status"] == "FROZEN_AFTER_INTERNAL_CI_PASS"
    assert lock["canonical_sha256"].startswith("sha256:")
    assert len(lock["canonical_sha256"]) == 71
    assert "does not establish" in lock["claims_boundary"].lower()
