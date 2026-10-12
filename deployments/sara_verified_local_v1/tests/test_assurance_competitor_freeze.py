from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_competitor_freeze_is_exact_and_digest_bound() -> None:
    root = _repo_root()
    manifest_path = root / "config" / "assurance_competitor_freeze_2026_09_17.json"
    digest_path = root / "config" / "assurance_competitor_freeze_2026_09_17.sha256"

    raw = manifest_path.read_bytes()
    expected_line = digest_path.read_text(encoding="utf-8").strip()
    expected_digest, filename = expected_line.split(maxsplit=1)
    assert filename == "assurance_competitor_freeze_2026_09_17.json"
    assert SHA256.fullmatch(expected_digest)
    assert hashlib.sha256(raw).hexdigest() == expected_digest

    data = json.loads(raw)
    assert data["status"] == "FROZEN_COMPARISON_INPUT_NOT_SCORED"
    assert data["composite_id"] == "best-of-breed-assurance-composite-2026-09-17"

    entries = data["entries"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    assert len(entries) >= 8

    for entry in entries:
        rendered = json.dumps(entry, sort_keys=True).lower()
        assert '"latest"' not in rendered
        assert "moving-latest" not in rendered
        assert entry["version"]
        assert entry["source"].startswith("https://")

        if entry["kind"] == "release_artifact":
            assert entry["artifact"]
            assert SHA256.fullmatch(entry["artifact_sha256"])
        elif entry["kind"] == "git_commit":
            assert GIT_SHA.fullmatch(entry["commit_sha"])
        elif entry["kind"] == "standard_reference":
            # Specifications are pinned by explicit published version and are
            # intentionally not misrepresented as executable artifacts.
            assert entry["version"].startswith("v")
            assert "artifact" not in entry
            assert "artifact_sha256" not in entry
        else:
            raise AssertionError(f"unsupported competitor freeze kind: {entry['kind']}")

        for support in entry.get("supporting_artifacts", []):
            assert support["artifact"]
            assert SHA256.fullmatch(support["sha256"])
