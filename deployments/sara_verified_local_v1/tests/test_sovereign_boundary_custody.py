from __future__ import annotations

import hashlib
import json

import pytest

from worldshepherd_sara.qualification import canonical_digest
from worldshepherd_sara.release_index_cli import RELEASE_INDEX_SCHEMA
from worldshepherd_sara.sovereign_boundary_custody import (
    ExecutionCustodyError,
    build_execution_custody,
)


def _release_index_bytes(*, commit_sha: str = "a" * 40) -> bytes:
    index = {
        "schema": RELEASE_INDEX_SCHEMA,
        "generated_utc": "2026-09-14T18:00:00Z",
        "repository": "Bdavis1390/Sara_pro",
        "commit_sha": commit_sha,
        "workflow": {
            "name": "SARA Verified Local v1 Gate",
            "run_id": "12345",
            "run_number": "1",
            "event_name": "pull_request",
            "ref": "refs/pull/265/merge",
            "pull_request_number": "265",
            "merge_state": "PR_CANDIDATE_UNMERGED",
        },
        "artifacts": {},
        "local_evidence": {},
        "claims_boundary": "test fixture; no operational claims",
    }
    index["release_index_digest"] = canonical_digest(index)
    return (json.dumps(index, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _attestation_receipt_bytes(index_bytes: bytes, *, commit_sha: str = "a" * 40) -> bytes:
    receipt = {
        "schema": "WS-SARA-RELEASE-ATTESTATION-RECEIPT-V1",
        "evidence_status": "GITHUB_SIGSTORE_ATTESTED_INTERNAL_RELEASE_INDEX",
        "triggering_commit_sha": commit_sha,
        "release_index_file_sha256": "sha256:" + hashlib.sha256(index_bytes).hexdigest(),
        "attestation_bundle_file_sha256": "sha256:" + "b" * 64,
        "attestation_id": "attestation:test:001",
        "attestation_url": "https://example.invalid/attestation/test-001",
    }
    return (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")


def test_execution_custody_reuses_release_index_digest_commit_and_attestation_file_binding():
    index_bytes = _release_index_bytes()
    receipt_bytes = _attestation_receipt_bytes(index_bytes)
    configuration = {
        "sara": {"mode": "lab", "port": 9530},
        "pep": {"physical_enabled": False},
    }

    custody = build_execution_custody(
        release_index_bytes=index_bytes,
        runtime_configuration=configuration,
        release_evidence_ref="artifact:sara-release-evidence-index:12345",
        attestation_receipt_bytes=receipt_bytes,
    )

    parsed = json.loads(index_bytes)
    assert custody.release_index_digest == parsed["release_index_digest"]
    assert custody.release_index_file_sha256 == "sha256:" + hashlib.sha256(index_bytes).hexdigest()
    assert custody.release_commit_sha == "a" * 40
    assert custody.release_merge_state == "PR_CANDIDATE_UNMERGED"
    assert custody.configuration_digest == canonical_digest(configuration)
    assert custody.attestation_id == "attestation:test:001"
    assert custody.attestation_receipt_file_sha256 == "sha256:" + hashlib.sha256(receipt_bytes).hexdigest()


def test_release_index_canonical_digest_mismatch_fails_closed():
    index = json.loads(_release_index_bytes())
    index["commit_sha"] = "c" * 40
    tampered = (json.dumps(index, sort_keys=True, indent=2) + "\n").encode("utf-8")

    with pytest.raises(ExecutionCustodyError, match="digest does not verify"):
        build_execution_custody(
            release_index_bytes=tampered,
            runtime_configuration={"mode": "lab"},
            release_evidence_ref="artifact:tampered",
        )


def test_attestation_receipt_for_different_release_file_fails_closed():
    index_bytes = _release_index_bytes()
    receipt = json.loads(_attestation_receipt_bytes(index_bytes))
    receipt["release_index_file_sha256"] = "sha256:" + "0" * 64
    mismatched_receipt = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")

    with pytest.raises(ExecutionCustodyError, match="does not bind"):
        build_execution_custody(
            release_index_bytes=index_bytes,
            runtime_configuration={"mode": "lab"},
            release_evidence_ref="artifact:release",
            attestation_receipt_bytes=mismatched_receipt,
        )


def test_configuration_digest_changes_when_runtime_configuration_changes():
    index_bytes = _release_index_bytes()
    first = build_execution_custody(
        release_index_bytes=index_bytes,
        runtime_configuration={"mode": "lab", "channel": 1},
        release_evidence_ref="artifact:release",
    )
    second = build_execution_custody(
        release_index_bytes=index_bytes,
        runtime_configuration={"mode": "lab", "channel": 2},
        release_evidence_ref="artifact:release",
    )
    assert first.release_index_digest == second.release_index_digest
    assert first.configuration_digest != second.configuration_digest
