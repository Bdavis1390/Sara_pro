from __future__ import annotations

import hashlib
import json

import pytest

from worldshepherd_sara.release_index_intake_link_cli import (
    INTAKE_ARTIFACT_KEY,
    INTAKE_ARTIFACT_NAME,
    link_intake_evidence,
    main,
)
from worldshepherd_sara.qualification import canonical_digest


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _release_index(path):
    _write_json(
        path,
        {
            "schema": "WS-SARA-RELEASE-EVIDENCE-INDEX-V1",
            "generated_utc": "2026-09-01T18:40:00Z",
            "repository": "Bdavis1390/Sara_pro",
            "commit_sha": "abc123",
            "workflow": {
                "name": "SARA Verified Local v1 Gate",
                "run_id": "33500000000",
                "run_number": "720",
                "event_name": "pull_request",
                "ref": "refs/pull/52/merge",
                "pull_request_number": "52",
                "merge_state": "PR_CANDIDATE_UNMERGED",
            },
            "artifacts": {
                "software_sbom_evidence": {
                    "name": "software-sbom-evidence",
                    "artifact_id": "111",
                    "artifact_digest": "sha256:" + "1" * 64,
                    "artifact_url": "https://github.example/sbom",
                }
            },
            "local_evidence": {"software_sbom_sha256": "sha256:" + "2" * 64},
            "claims_boundary": "Release index records CI evidence custody only. It does not establish partner validation.",
            "release_index_digest": "sha256:" + "3" * 64,
        },
    )


def _intake_dir(root):
    intake_dir = root / "intake_minimum_ci"
    record = {
        "intake_id": "INTAKE-001",
        "human_review_status": "PENDING_HUMAN_REVIEW",
        "routing_status": "ROUTED_TO_BACKLOG",
        "minimum_controls": {
            "source_custody": "PASS",
            "source_hash": "PASS",
            "claims_boundary": "PASS",
            "human_review_status": "PASS",
            "routing_status": "PASS",
            "downstream_route_or_evidence": "PASS",
            "false_claim_guard": "PASS",
        },
    }
    record["record_digest"] = canonical_digest(record)
    ledger = {
        "schema": "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1",
        "records": [record],
        "summary": {
            "intake_count": 1,
            "pending_human_review_count": 1,
            "reviewed_action_required_count": 0,
            "not_material_count": 0,
            "review_counts": {"PENDING_HUMAN_REVIEW": 1},
            "routing_counts": {"ROUTED_TO_BACKLOG": 1},
        },
        "claims_boundary": "Intake ledger does not establish source truth.",
    }
    ledger["ledger_digest"] = canonical_digest(ledger)
    ledger_path = intake_dir / "intake-minimum-ledger.json"
    _write_json(ledger_path, ledger)
    _write_json(
        intake_dir / "intake-minimum-summary.json",
        {
            "schema": "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1",
            "evidence_status": "INTERNAL_INTAKE_STANDARD_UNSIGNED",
            "intake_count": 1,
            "pending_human_review_count": 1,
            "reviewed_action_required_count": 0,
            "not_material_count": 0,
            "review_counts": {"PENDING_HUMAN_REVIEW": 1},
            "routing_counts": {"ROUTED_TO_BACKLOG": 1},
            "intake_minimum_ledger_sha256": ledger["ledger_digest"],
            "intake_minimum_ledger_file_sha256": _sha256_file(ledger_path),
            "input_files": {"intake_file": {"sha256": "sha256:" + "6" * 64}},
            "claims_boundary": "Intake minimum evidence does not establish source truth or operational authority.",
        },
    )
    return intake_dir


def test_link_intake_evidence_adds_artifact_and_local_custody(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)

    linked = link_intake_evidence(
        release_index_path=release_index,
        intake_dir=intake_dir,
        intake_artifact_id="777",
        intake_artifact_digest="sha256:" + "7" * 64,
        intake_artifact_url="https://github.example/intake",
    )

    artifact = linked["artifacts"][INTAKE_ARTIFACT_KEY]
    assert artifact["name"] == INTAKE_ARTIFACT_NAME
    assert artifact["artifact_id"] == "777"
    assert artifact["artifact_digest"] == "sha256:" + "7" * 64
    assert linked["local_evidence"]["intake_minimum_intake_count"] == 1
    assert linked["local_evidence"]["intake_minimum_pending_human_review_count"] == 1
    assert linked["local_evidence"]["intake_minimum_ledger_digest"].startswith("sha256:")
    assert linked["local_evidence"]["intake_minimum_summary_sha256"].startswith("sha256:")
    assert linked["local_evidence"]["intake_minimum_ledger_sha256"].startswith("sha256:")
    assert linked["release_index_digest"].startswith("sha256:")
    assert linked["release_index_digest"] != "sha256:" + "3" * 64
    assert "intake evidence linkage does not establish source truth" in linked["claims_boundary"].lower()


def test_release_index_intake_link_cli_writes_in_place(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)

    exit_code = main(
        [
            "--release-index",
            str(release_index),
            "--intake-dir",
            str(intake_dir),
            "--intake-artifact-id",
            "888",
            "--intake-artifact-digest",
            "sha256:" + "8" * 64,
            "--intake-artifact-url",
            "https://github.example/intake",
        ]
    )

    assert exit_code == 0
    written = json.loads(release_index.read_text(encoding="utf-8"))
    assert written["artifacts"][INTAKE_ARTIFACT_KEY]["artifact_id"] == "888"
    assert written["local_evidence"]["intake_minimum_evidence_status"] == "INTERNAL_INTAKE_STANDARD_UNSIGNED"


def test_link_intake_evidence_rejects_bad_digest(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)

    with pytest.raises(ValueError, match="must be a SHA-256 digest"):
        link_intake_evidence(
            release_index_path=release_index,
            intake_dir=intake_dir,
            intake_artifact_id="777",
            intake_artifact_digest="not-a-digest",
            intake_artifact_url=None,
        )


def test_link_intake_evidence_rejects_bad_summary_schema(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)
    _write_json(intake_dir / "intake-minimum-summary.json", {"schema": "WRONG"})

    with pytest.raises(ValueError, match="unexpected intake minimum summary schema"):
        link_intake_evidence(
            release_index_path=release_index,
            intake_dir=intake_dir,
            intake_artifact_id="777",
            intake_artifact_digest="sha256:" + "7" * 64,
            intake_artifact_url=None,
        )


def test_link_intake_evidence_rejects_ledger_file_digest_mismatch(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)
    ledger_path = intake_dir / "intake-minimum-ledger.json"
    ledger_path.write_text(ledger_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ledger file digest mismatch"):
        link_intake_evidence(
            release_index_path=release_index,
            intake_dir=intake_dir,
            intake_artifact_id="777",
            intake_artifact_digest="sha256:" + "7" * 64,
            intake_artifact_url=None,
        )


def test_link_intake_evidence_rejects_canonical_ledger_digest_mismatch(tmp_path) -> None:
    release_index = tmp_path / "release_index_ci" / "release-index.json"
    _release_index(release_index)
    intake_dir = _intake_dir(tmp_path)
    ledger_path = intake_dir / "intake-minimum-ledger.json"
    summary_path = intake_dir / "intake-minimum-summary.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["claims_boundary"] = "Tampered content that does not establish source truth."
    _write_json(ledger_path, ledger)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["intake_minimum_ledger_file_sha256"] = _sha256_file(ledger_path)
    _write_json(summary_path, summary)

    with pytest.raises(ValueError, match="canonical ledger digest mismatch"):
        link_intake_evidence(
            release_index_path=release_index,
            intake_dir=intake_dir,
            intake_artifact_id="777",
            intake_artifact_digest="sha256:" + "7" * 64,
            intake_artifact_url=None,
        )
