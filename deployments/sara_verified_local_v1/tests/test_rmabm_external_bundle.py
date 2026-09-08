from __future__ import annotations

from pathlib import Path

import pytest

from worldshepherd_sara.rmabm_external_bundle import (
    SAFE_RELATIVE_PATHS,
    build_external_evidence_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_current_allowlisted_external_candidate_set_builds_deterministically():
    first = build_external_evidence_manifest(
        repository_root=REPO_ROOT,
        relative_paths=SAFE_RELATIVE_PATHS,
    )
    second = build_external_evidence_manifest(
        repository_root=REPO_ROOT,
        relative_paths=reversed(sorted(SAFE_RELATIVE_PATHS)),
    )

    assert len(first.artifacts) == len(SAFE_RELATIVE_PATHS)
    assert first == second
    assert len(first.manifest_sha256) == 64
    assert all(len(artifact.sha256) == 64 for artifact in first.artifacts)


def test_non_allowlisted_file_is_rejected(tmp_path: Path):
    relative_path = "private_notes.txt"
    (tmp_path / relative_path).write_text("ordinary text", encoding="utf-8")

    with pytest.raises(ValueError, match="not allowlisted"):
        build_external_evidence_manifest(
            repository_root=tmp_path,
            relative_paths=[relative_path],
        )


def test_email_address_in_allowlisted_candidate_is_rejected(tmp_path: Path):
    relative_path = "docs/golden_dome/GD-08_GOLDEN_DOME_HUB_CAPABILITY_OVERVIEW.md"
    candidate = tmp_path / relative_path
    candidate.parent.mkdir(parents=True)
    candidate.write_text("Contact: example.person@example.com", encoding="utf-8")

    with pytest.raises(ValueError, match="contains an email address"):
        build_external_evidence_manifest(
            repository_root=tmp_path,
            relative_paths=[relative_path],
        )


def test_secret_like_assignment_in_allowlisted_candidate_is_rejected(tmp_path: Path):
    relative_path = "docs/golden_dome/GD-08_GOLDEN_DOME_HUB_CAPABILITY_OVERVIEW.md"
    candidate = tmp_path / relative_path
    candidate.parent.mkdir(parents=True)
    candidate.write_text("api_key=do-not-release", encoding="utf-8")

    with pytest.raises(ValueError, match="secret-like material"):
        build_external_evidence_manifest(
            repository_root=tmp_path,
            relative_paths=[relative_path],
        )


def test_repository_escape_is_rejected(tmp_path: Path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("ordinary text", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes repository root"):
        build_external_evidence_manifest(
            repository_root=tmp_path,
            relative_paths=["../outside.md"],
        )
