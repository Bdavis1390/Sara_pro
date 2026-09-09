from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from worldshepherd_sara.isolated_custody_client import AuthorityUnavailable, CustodyClient
import worldshepherd_sara.isolated_custody_client as client_module


def _wait_for_socket(path: Path) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError("authority socket did not appear")


@pytest.fixture
def authority(tmp_path: Path):
    socket_path = tmp_path / "authority.sock"
    db_path = tmp_path / "authority.sqlite3"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "worldshepherd_sara.isolated_custody_service",
            "--socket",
            str(socket_path),
            "--db",
            str(db_path),
            "--authorized-resolution-uid",
            str(os.getuid()),
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_socket(socket_path)
        yield CustodyClient(str(socket_path)), process, socket_path
    finally:
        process.terminate()
        process.wait(timeout=5)


def _registered(client: CustodyClient, package_id: str = "pkg-1") -> None:
    response = client.register_package(
        package_id=package_id,
        authority_required="CRE1AWS",
        required_evidence_types=["TEST"],
        baseline_id="base-1",
    )
    assert response["ok"] is True


def _ingest(client: CustodyClient, package_id: str = "pkg-1") -> None:
    response = client.ingest_evidence(
        package_id=package_id,
        evidence_id="e-1",
        evidence_type="TEST",
        version=1,
        baseline_id="base-1",
        record={"measurement": 7, "source": "synthetic"},
    )
    assert response["ok"] is True


def test_client_has_no_authoritative_state_or_signing_material(authority):
    client, _process, _socket = authority
    _registered(client)
    names = set(vars(client_module))
    assert "_RESOLUTION_VAULT" not in names
    assert "_IDENTITY_CUSTODY" not in names
    assert "_resolution_key" not in names
    assert not hasattr(client, "_custody")
    for value in vars(client_module).values():
        if isinstance(value, (bytes, bytearray)):
            assert len(value) != 32


def test_snapshot_mutation_does_not_change_authoritative_state(authority):
    client, _process, _socket = authority
    _registered(client)
    _ingest(client)
    snapshot = client.get_snapshot("pkg-1")["snapshot"]
    snapshot["closed"] = True
    snapshot["evidence"].clear()
    fresh = client.get_snapshot("pkg-1")["snapshot"]
    assert fresh["closed"] is False
    assert len(fresh["evidence"]) == 1


def test_post_closure_ingest_rejected_despite_client_mutation(authority):
    client, _process, _socket = authority
    _registered(client)
    _ingest(client)
    assert client.close_package("pkg-1")["ok"] is True
    forged = client.get_snapshot("pkg-1")["snapshot"]
    forged["closed"] = False
    response = client.ingest_evidence(
        package_id="pkg-1",
        evidence_id="e-2",
        evidence_type="TEST",
        version=2,
        baseline_id="base-1",
        record={"measurement": 8, "source": "synthetic"},
    )
    assert response["ok"] is False
    assert response["error"] == "package_closed"


def test_one_shot_registration_is_service_owned(authority):
    client, _process, _socket = authority
    request_id = "register-1"
    first = client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id=request_id,
    )
    second = client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id=request_id,
    )
    assert first == second
    conflict = client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-2",
    )
    assert conflict["ok"] is False


def test_request_id_reuse_with_different_payload_is_rejected(authority):
    client, _process, _socket = authority
    first = client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="same-id",
    )
    assert first["ok"] is True
    second = client.register_package(
        package_id="pkg-2",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="same-id",
    )
    assert second["ok"] is False
    assert second["error"] == "request_id_reuse_mismatch"


def test_unknown_generic_sign_operation_is_rejected(authority):
    client, _process, _socket = authority
    response = client._request("sign", {"payload": "forged"})
    assert response["ok"] is False
    assert response["error"] == "unknown_operation"


def test_resolution_is_service_authorized_and_snapshot_is_detached(authority):
    client, _process, _socket = authority
    _registered(client)
    client.open_issue(package_id="pkg-1", issue="REVIEW_REQUIRED")
    resolved = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
    )
    assert resolved["ok"] is True
    snapshot = resolved["snapshot"]
    assert snapshot["open_issues"] == []
    assert snapshot["resolutions"][0]["tag"].startswith("hmac-sha256:")
    snapshot["resolutions"][0]["actor"] = "forged"
    fresh = client.get_snapshot("pkg-1")["snapshot"]
    assert fresh["resolutions"][0]["actor"] == "operator"


def test_authority_unavailable_fails_closed(tmp_path: Path):
    client = CustodyClient(str(tmp_path / "missing.sock"), timeout_seconds=0.1)
    with pytest.raises(AuthorityUnavailable):
        client.health()


def test_client_functions_do_not_capture_service_store(authority):
    client, _process, _socket = authority
    for _name, member in inspect.getmembers(client.__class__, predicate=inspect.isfunction):
        closure = member.__closure__ or ()
        contents = [cell.cell_contents for cell in closure]
        assert all(value.__class__.__name__ != "AuthorityStore" for value in contents)


def test_service_restart_preserves_closed_lifecycle(tmp_path: Path):
    socket_path = tmp_path / "authority.sock"
    db_path = tmp_path / "authority.sqlite3"

    def start():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "worldshepherd_sara.isolated_custody_service",
                "--socket",
                str(socket_path),
                "--db",
                str(db_path),
                "--authorized-resolution-uid",
                str(os.getuid()),
            ],
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_socket(socket_path)
        return process

    first = start()
    try:
        client = CustodyClient(str(socket_path))
        client.register_package(
            package_id="pkg-r",
            authority_required="CRE1AWS",
            required_evidence_types=[],
            baseline_id="base-1",
        )
        assert client.close_package("pkg-r")["ok"] is True
    finally:
        first.terminate()
        first.wait(timeout=5)
        if socket_path.exists():
            socket_path.unlink()

    second = start()
    try:
        client = CustodyClient(str(socket_path))
        snapshot = client.get_snapshot("pkg-r")["snapshot"]
        assert snapshot["closed"] is True
        rejected = client.ingest_evidence(
            package_id="pkg-r",
            evidence_id="late",
            evidence_type="TEST",
            version=1,
            baseline_id="base-1",
            record={"late": True},
        )
        assert rejected["ok"] is False
        assert rejected["error"] == "package_closed"
    finally:
        second.terminate()
        second.wait(timeout=5)
