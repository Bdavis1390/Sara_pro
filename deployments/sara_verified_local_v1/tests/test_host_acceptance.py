from __future__ import annotations

import hashlib
import json
from pathlib import Path

from worldshepherd_sara.host_acceptance import assess_actual_host_evidence


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _build_valid_evidence(root: Path) -> str:
    branch = "worldshepherd/pvk-v0.5-cross-project-20260906"
    commit = "a" * 40
    record_id = "PHYS-HOST-20260907T001500Z"
    shadow_port = 19530

    _write(
        root / "RESULT.txt",
        "\n".join(
            [
                "ACTUAL_HOST_PVK_SHADOW_ACCEPTANCE=PASS",
                f"branch={branch}",
                f"commit={commit}",
                f"shadow_port={shadow_port}",
                "relay_admin_boundary=PASS",
                "pvk_record_append=PASS",
                "pvk_claims_linter=PASS",
                "pvk_restart_persistence=PASS",
                "pvk_audit_presence=PASS",
                "scientific_validation_claim=NOT_ESTABLISHED_BY_THIS_TEST",
            ]
        )
        + "\n",
    )
    _write(
        root / "baseline.txt",
        "\n".join(
            [
                "schema=WS-ACTUAL-HOST-PVK-ACCEPTANCE-V1",
                "timestamp_utc=20260907T001500Z",
                "hostname=worldshepherd-host",
                "kernel=Linux 6.8.0 x86_64 GNU/Linux",
                "os_release=Ubuntu 22.04 LTS",
                f"git_branch={branch}",
                f"git_head={commit}",
                "docker_version=Docker version 28.5.2",
                "compose_version=Docker Compose version v2.39.0",
                "shadow_project=ws_pvk_host_20260907t001500z",
                f"shadow_base_url=http://127.0.0.1:{shadow_port}",
            ]
        )
        + "\n",
    )
    _write(root / "authorization.txt", "relay_pvk_status_http=403\n")
    _write(root / "physics-status.initial.json", json.dumps({"ok": True}) + "\n")
    _write(
        root / "record-append.json",
        json.dumps(
            {
                "accepted": True,
                "record": {
                    "record_id": record_id,
                    "validation_state": "concept",
                    "claim_label": "IMPLEMENTED IN SOFTWARE",
                },
            }
        )
        + "\n",
    )
    _write(
        root / "lint-response.json",
        json.dumps(
            {
                "blocked": True,
                "findings": [{"rule_id": "PROP-01", "severity": "BLOCK"}],
            }
        )
        + "\n",
    )
    _write(
        root / "physics-records.after-restart.json",
        json.dumps({"records": [{"record_id": record_id}]}) + "\n",
    )
    _write(
        root / "audit.after-restart.PRIVATE.json",
        json.dumps(
            {
                "records": [
                    {"event": "service_started"},
                    {"event": "physics_record_appended"},
                    {"event": "physics_claim_linted"},
                ]
            }
        )
        + "\n",
    )
    _write(
        root / "compose.ps.txt",
        (
            "NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS\n"
            f"sara image cmd sara now Up 127.0.0.1:{shadow_port}->9530/tcp\n"
        ),
    )
    _write(root / "compose.rendered.PRIVATE.yaml", "services: {}\n")
    _write(root / "build.log", "build ok\n")

    names = sorted(path.name for path in root.iterdir() if path.name != "SHA256SUMS")
    manifest = "".join(
        f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  ./{name}\n"
        for name in names
    )
    _write(root / "SHA256SUMS", manifest)
    return commit


def _rehash(root: Path) -> None:
    names = sorted(path.name for path in root.iterdir() if path.name != "SHA256SUMS")
    manifest = "".join(
        f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  ./{name}\n"
        for name in names
    )
    _write(root / "SHA256SUMS", manifest)


def test_valid_actual_host_package_is_accepted(tmp_path: Path):
    commit = _build_valid_evidence(tmp_path)
    result = assess_actual_host_evidence(
        tmp_path,
        expected_branch="worldshepherd/pvk-v0.5-cross-project-20260906",
        expected_commit=commit,
    )
    assert result.accepted is True
    assert result.blockers == ()
    assert result.record_id and result.record_id.startswith("PHYS-HOST-")
    assert result.as_dict()["scientific_validation_claim"] == (
        "NOT_ESTABLISHED_BY_HOST_ACCEPTANCE"
    )


def test_tamper_is_rejected(tmp_path: Path):
    _build_valid_evidence(tmp_path)
    _write(tmp_path / "authorization.txt", "relay_pvk_status_http=200\n")
    result = assess_actual_host_evidence(tmp_path)
    assert result.accepted is False
    assert "SHA256_MISMATCH:authorization.txt" in result.blockers
    assert "RELAY_ADMIN_BOUNDARY_NOT_403" in result.blockers


def test_wrong_commit_is_rejected(tmp_path: Path):
    _build_valid_evidence(tmp_path)
    result = assess_actual_host_evidence(tmp_path, expected_commit="b" * 40)
    assert result.accepted is False
    assert "UNEXPECTED_COMMIT" in result.blockers


def test_wildcard_or_missing_loopback_mapping_is_rejected(tmp_path: Path):
    _build_valid_evidence(tmp_path)
    _write(
        tmp_path / "compose.ps.txt",
        "NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS\n"
        "sara image cmd sara now Up 0.0.0.0:19530->9530/tcp\n",
    )
    _rehash(tmp_path)
    result = assess_actual_host_evidence(tmp_path)
    assert result.accepted is False
    assert "SHADOW_LOOPBACK_BINDING_NOT_PROVEN" in result.blockers
    assert "SHADOW_WILDCARD_BINDING_DETECTED" in result.blockers


def test_missing_host_identity_field_is_rejected(tmp_path: Path):
    _build_valid_evidence(tmp_path)
    baseline = (tmp_path / "baseline.txt").read_text(encoding="utf-8")
    baseline = baseline.replace("hostname=worldshepherd-host\n", "")
    _write(tmp_path / "baseline.txt", baseline)
    _rehash(tmp_path)
    result = assess_actual_host_evidence(tmp_path)
    assert result.accepted is False
    assert "BASELINE_FIELD_MISSING:hostname" in result.blockers
