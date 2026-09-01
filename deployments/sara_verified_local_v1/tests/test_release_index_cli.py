from __future__ import annotations

import json

import pytest

from worldshepherd_sara.release_index_cli import (
    MERGE_STATE_MAIN_PUSH,
    MERGE_STATE_MANUAL_OR_NON_MAIN,
    MERGE_STATE_PR_CANDIDATE,
    RELEASE_INDEX_SCHEMA,
    build_release_evidence_index,
    derive_merge_state,
    main,
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_evidence_dirs(tmp_path):
    pre_dir = tmp_path / "qualification_evidence_ci"
    partner_dir = tmp_path / "partner_screening_ci"
    _write_json(
        pre_dir / "qualification_index.json",
        {
            "schema": "WS-PRE-FULL-BLOOM-QUALIFICATION-INDEX-V1",
            "bundle_digests": {"apnt": "sha256:" + "1" * 64},
            "claims_boundary": ["No external reproduction or partner validation claim."],
        },
    )
    _write_json(
        partner_dir / "batch-manifest.json",
        {
            "schema": "WS-PARTNER-SCREENING-BATCH-MANIFEST-V1",
            "partners": ["BAE_SYSTEMS", "GENERIC_PRIME"],
            "lanes": ["apnt", "geo_prov"],
            "source_bundle_count": 2,
            "package_count": 4,
            "batch_digest": "sha256:" + "2" * 64,
            "claims_boundary": "Batch screening export only; no partner validation claim.",
        },
    )
    return pre_dir, partner_dir


def test_release_index_records_ci_artifacts_and_claims_boundary(tmp_path) -> None:
    pre_dir, partner_dir = _make_evidence_dirs(tmp_path)

    index = build_release_evidence_index(
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        workflow_name="SARA Verified Local v1 Gate",
        workflow_run_id="33500000000",
        workflow_run_number="653",
        event_name="pull_request",
        ref="refs/pull/44/merge",
        pr_number="44",
        merge_state=MERGE_STATE_PR_CANDIDATE,
        pre_dir=pre_dir,
        partner_dir=partner_dir,
        pre_artifact_id="111",
        pre_artifact_digest="sha256:" + "a" * 64,
        pre_artifact_url="https://github.example/pre",
        partner_artifact_id="222",
        partner_artifact_digest="b" * 64,
        partner_artifact_url="https://github.example/partner",
        executed_utc="2026-09-01T17:10:00Z",
    )

    assert index["schema"] == RELEASE_INDEX_SCHEMA
    assert index["commit_sha"] == "abc123"
    assert index["workflow"]["pull_request_number"] == "44"
    assert index["workflow"]["merge_state"] == MERGE_STATE_PR_CANDIDATE
    assert index["artifacts"]["pre_full_bloom_qualification_evidence"]["artifact_digest"] == "sha256:" + "a" * 64
    assert index["artifacts"]["partner_screening_batch_evidence"]["artifact_digest"] == "sha256:" + "b" * 64
    assert index["local_evidence"]["partner_batch_digest"] == "sha256:" + "2" * 64
    assert index["local_evidence"]["partner_package_count"] == 4
    assert index["local_evidence"]["partner_presets"] == ["BAE_SYSTEMS", "GENERIC_PRIME"]
    assert index["release_index_digest"].startswith("sha256:")
    assert "does not establish partner validation" in index["claims_boundary"]


def test_release_index_cli_writes_main_push_index_file(tmp_path) -> None:
    pre_dir, partner_dir = _make_evidence_dirs(tmp_path)
    out_path = tmp_path / "release_index_ci" / "release-index.json"

    exit_code = main(
        [
            "--out",
            str(out_path),
            "--pre-dir",
            str(pre_dir),
            "--partner-dir",
            str(partner_dir),
            "--repository",
            "Bdavis1390/Sara_pro",
            "--commit-sha",
            "abc123",
            "--workflow-name",
            "SARA Verified Local v1 Gate",
            "--workflow-run-id",
            "33500000001",
            "--workflow-run-number",
            "654",
            "--event-name",
            "push",
            "--ref",
            "refs/heads/main",
            "--pre-artifact-id",
            "111",
            "--pre-artifact-digest",
            "sha256:" + "c" * 64,
            "--partner-artifact-id",
            "222",
            "--partner-artifact-digest",
            "sha256:" + "d" * 64,
            "--executed-utc",
            "2026-09-01T17:11:00Z",
        ]
    )

    assert exit_code == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["schema"] == RELEASE_INDEX_SCHEMA
    assert written["workflow"]["event_name"] == "push"
    assert written["workflow"]["ref"] == "refs/heads/main"
    assert written["workflow"]["pull_request_number"] is None
    assert written["workflow"]["merge_state"] == MERGE_STATE_MAIN_PUSH


def test_release_index_derives_manual_or_non_main_state() -> None:
    assert derive_merge_state(event_name="workflow_dispatch", ref="refs/heads/main") == MERGE_STATE_MANUAL_OR_NON_MAIN
    assert derive_merge_state(event_name="push", ref="refs/heads/feature") == MERGE_STATE_MANUAL_OR_NON_MAIN


def test_release_index_rejects_bad_artifact_digest(tmp_path) -> None:
    pre_dir, partner_dir = _make_evidence_dirs(tmp_path)

    with pytest.raises(ValueError, match="must be a SHA-256 digest"):
        build_release_evidence_index(
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            workflow_name="SARA Verified Local v1 Gate",
            workflow_run_id="33500000002",
            workflow_run_number="655",
            event_name="pull_request",
            ref="refs/pull/44/merge",
            pr_number="44",
            merge_state=MERGE_STATE_PR_CANDIDATE,
            pre_dir=pre_dir,
            partner_dir=partner_dir,
            pre_artifact_id="111",
            pre_artifact_digest="not-a-digest",
            pre_artifact_url=None,
            partner_artifact_id="222",
            partner_artifact_digest="sha256:" + "e" * 64,
            partner_artifact_url=None,
        )


def test_release_index_rejects_merge_state_mismatch(tmp_path) -> None:
    pre_dir, partner_dir = _make_evidence_dirs(tmp_path)

    with pytest.raises(ValueError, match="does not match event/ref context"):
        build_release_evidence_index(
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            workflow_name="SARA Verified Local v1 Gate",
            workflow_run_id="33500000003",
            workflow_run_number="656",
            event_name="push",
            ref="refs/heads/main",
            pr_number=None,
            merge_state=MERGE_STATE_PR_CANDIDATE,
            pre_dir=pre_dir,
            partner_dir=partner_dir,
            pre_artifact_id="111",
            pre_artifact_digest="sha256:" + "f" * 64,
            pre_artifact_url=None,
            partner_artifact_id="222",
            partner_artifact_digest="sha256:" + "e" * 64,
            partner_artifact_url=None,
        )
