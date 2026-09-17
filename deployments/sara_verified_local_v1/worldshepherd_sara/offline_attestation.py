from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RECEIPT_SCHEMA = "WS-SARA-OFFLINE-ATTESTATION-VERIFY-V1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_verify_command(
    *,
    artifact: Path,
    bundle: Path,
    trusted_root: Path,
    repository: str,
    gh_executable: str = "gh",
) -> list[str]:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("repository must be in owner/name form")
    return [
        gh_executable,
        "attestation",
        "verify",
        str(artifact),
        "-R",
        repository,
        "--bundle",
        str(bundle),
        "--custom-trusted-root",
        str(trusted_root),
    ]


def verify_offline_attestation(
    *,
    artifact: str | Path,
    bundle: str | Path,
    trusted_root: str | Path,
    repository: str,
    gh_executable: str = "gh",
    runner: Callable[..., Any] = subprocess.run,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    artifact_path = Path(artifact).resolve()
    bundle_path = Path(bundle).resolve()
    trusted_root_path = Path(trusted_root).resolve()

    for label, path in (
        ("artifact", artifact_path),
        ("bundle", bundle_path),
        ("trusted_root", trusted_root_path),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} file does not exist: {path}")
        if path.stat().st_size == 0:
            raise ValueError(f"{label} file is empty: {path}")

    resolved_gh = shutil.which(gh_executable)
    if resolved_gh is None:
        raise FileNotFoundError(
            f"GitHub CLI executable not found on PATH: {gh_executable!r}"
        )

    command = build_verify_command(
        artifact=artifact_path,
        bundle=bundle_path,
        trusted_root=trusted_root_path,
        repository=repository,
        gh_executable=resolved_gh,
    )

    completed = runner(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(
            "offline attestation verification failed"
            + (f": {stderr[:2000]}" if stderr else "")
        )

    timestamp = (now or (lambda: datetime.now(timezone.utc)))()
    if timestamp.tzinfo is None:
        raise ValueError("verification timestamp must be timezone-aware")

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "verification_status": "PASS",
        "verified_utc": timestamp.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "repository": repository,
        "artifact": {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
        },
        "bundle": {
            "path": bundle_path.name,
            "sha256": sha256_file(bundle_path),
        },
        "trusted_root": {
            "path": trusted_root_path.name,
            "sha256": sha256_file(trusted_root_path),
        },
        "verifier": {
            "tool": "gh attestation verify",
            "executable": resolved_gh,
            "offline_inputs_explicit": True,
        },
        "claims_boundary": (
            "PASS establishes verification of the supplied artifact against the supplied "
            "attestation bundle and trusted-root material using GitHub CLI offline verification. "
            "It does not independently validate claims contained inside the artifact, establish "
            "customer/government acceptance, certification, operational effectiveness, or "
            "independent reproduction of higher-level Worldshepherd behavior."
        ),
    }
    return receipt


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return json.dumps(
        receipt,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_receipt_bytes(receipt)).hexdigest()
