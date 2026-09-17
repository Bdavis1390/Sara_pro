from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import worldshepherd_sara.offline_attestation as offline


def test_build_verify_command_uses_explicit_offline_inputs(tmp_path) -> None:
    artifact = tmp_path / "release-index.json"
    bundle = tmp_path / "bundle.json"
    root = tmp_path / "trusted-root.jsonl"
    command = offline.build_verify_command(
        artifact=artifact,
        bundle=bundle,
        trusted_root=root,
        repository="Bdavis1390/Sara_pro",
        gh_executable="/usr/bin/gh",
    )
    assert command == [
        "/usr/bin/gh",
        "attestation",
        "verify",
        str(artifact),
        "-R",
        "Bdavis1390/Sara_pro",
        "--bundle",
        str(bundle),
        "--custom-trusted-root",
        str(root),
    ]


def test_invalid_repository_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        offline.build_verify_command(
            artifact=tmp_path / "a",
            bundle=tmp_path / "b",
            trusted_root=tmp_path / "c",
            repository="not-a-repository",
        )


def test_missing_input_fails_before_verifier_execution(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        offline.verify_offline_attestation(
            artifact=tmp_path / "missing",
            bundle=tmp_path / "bundle",
            trusted_root=tmp_path / "root",
            repository="Bdavis1390/Sara_pro",
        )


def test_verifier_failure_is_not_converted_to_pass(tmp_path, monkeypatch) -> None:
    artifact = tmp_path / "release-index.json"
    bundle = tmp_path / "bundle.json"
    root = tmp_path / "trusted-root.jsonl"
    for path in (artifact, bundle, root):
        path.write_text("fixture\n", encoding="utf-8")

    monkeypatch.setattr(offline.shutil, "which", lambda _: "/usr/bin/gh")

    def fail_runner(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="signature mismatch")

    with pytest.raises(RuntimeError, match="signature mismatch"):
        offline.verify_offline_attestation(
            artifact=artifact,
            bundle=bundle,
            trusted_root=root,
            repository="Bdavis1390/Sara_pro",
            runner=fail_runner,
        )


def test_success_receipt_binds_all_three_inputs(tmp_path, monkeypatch) -> None:
    artifact = tmp_path / "release-index.json"
    bundle = tmp_path / "bundle.json"
    root = tmp_path / "trusted-root.jsonl"
    artifact.write_text('{"release":"fixture"}\n', encoding="utf-8")
    bundle.write_text('{"bundle":"fixture"}\n', encoding="utf-8")
    root.write_text('{"root":"fixture"}\n', encoding="utf-8")

    monkeypatch.setattr(offline.shutil, "which", lambda _: "/usr/bin/gh")
    calls = []

    def pass_runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="verified", stderr="")

    receipt = offline.verify_offline_attestation(
        artifact=artifact,
        bundle=bundle,
        trusted_root=root,
        repository="Bdavis1390/Sara_pro",
        runner=pass_runner,
        now=lambda: datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc),
    )

    assert receipt["verification_status"] == "PASS"
    assert receipt["verified_utc"] == "2026-09-17T20:00:00Z"
    assert receipt["artifact"]["sha256"] == offline.sha256_file(artifact)
    assert receipt["bundle"]["sha256"] == offline.sha256_file(bundle)
    assert receipt["trusted_root"]["sha256"] == offline.sha256_file(root)
    assert calls[0][0][0:3] == ["/usr/bin/gh", "attestation", "verify"]
    assert "--bundle" in calls[0][0]
    assert "--custom-trusted-root" in calls[0][0]
