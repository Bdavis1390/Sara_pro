from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from worldshepherd_sara.isolated_custody_client import AuthorityUnavailable, CustodyClient
from worldshepherd_sara.isolated_custody_service import (
    AUTH_SCHEMA,
    SCHEMA_VERSION,
    AuthorityServer,
    AuthorityStore,
)
import worldshepherd_sara.isolated_custody_client as client_module


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _wait_for_socket(path: Path) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError("authority socket did not appear")


def _write_key(path: Path, key: bytes) -> None:
    path.write_bytes(key)
    os.chmod(path, 0o600)


def _authorization(
    key: bytes,
    *,
    package_id="pkg-1",
    issue="REVIEW_REQUIRED",
    actor="operator",
    role="CRE1AWS",
    rationale="synthetic test authorization",
    token_id=None,
    expires_at=None,
):
    fields = {
        "token_id": token_id or str(uuid.uuid4()),
        "operation": "resolve_issue",
        "package_id": package_id,
        "issue": issue,
        "actor": actor,
        "role": role,
        "rationale": rationale,
        "expires_at": int(expires_at or (time.time() + 300)),
    }
    tag = hmac.new(key, _canonical({"schema": AUTH_SCHEMA, **fields}), hashlib.sha256).hexdigest()
    return {"schema": AUTH_SCHEMA, **fields, "tag": "hmac-sha256:" + tag}


def _start(tmp_path: Path, authorization_key: bytes, provenance_key: bytes):
    socket_path = tmp_path / "authority.sock"
    db_path = tmp_path / "authority.sqlite3"
    auth_path = tmp_path / "authorization.key"
    provenance_path = tmp_path / "provenance.key"
    _write_key(auth_path, authorization_key)
    _write_key(provenance_path, provenance_key)

    # CI cannot create a second real UID. The subprocess monkeypatch affects only
    # the service's startup identity check; Linux SO_PEERCRED still reports the
    # process's real UID, so client/server peer authentication remains exercised.
    fake_authority_uid = os.getuid() + 100000
    code = (
        "import os; "
        f"os.getuid=lambda:{fake_authority_uid}; "
        "from worldshepherd_sara.isolated_custody_service import main; main()"
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            code,
            "--socket",
            str(socket_path),
            "--db",
            str(db_path),
            "--authorization-key-file",
            str(auth_path),
            "--provenance-key-file",
            str(provenance_path),
            "--allowed-client-uid",
            str(os.getuid()),
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_socket(socket_path)
    assert not auth_path.exists()
    assert not provenance_path.exists()
    return (
        process,
        CustodyClient(str(socket_path), expected_authority_uid=os.getuid()),
        socket_path,
        db_path,
    )


@pytest.fixture
def authority(tmp_path: Path):
    auth_key = os.urandom(32)
    provenance_key = os.urandom(32)
    process, client, socket_path, _db = _start(tmp_path, auth_key, provenance_key)
    try:
        yield client, process, socket_path, auth_key, provenance_key
    finally:
        process.terminate()
        process.wait(timeout=5)


def _registered(client: CustodyClient, package_id="pkg-1", required=("TEST",)):
    assert client.register_package(
        package_id=package_id,
        authority_required="CRE1AWS",
        required_evidence_types=list(required),
        baseline_id="base-1",
    )["ok"]


def _ingest(client: CustodyClient, package_id="pkg-1"):
    assert client.ingest_evidence(
        package_id=package_id,
        evidence_id="e-1",
        evidence_type="TEST",
        version=1,
        baseline_id="base-1",
        record={"measurement": 7, "source": "synthetic"},
    )["ok"]


def test_client_has_no_authoritative_state_or_signing_material(authority):
    client, _, _, _, _ = authority
    _registered(client)
    names = set(vars(client_module))
    assert "_RESOLUTION_VAULT" not in names
    assert "_IDENTITY_CUSTODY" not in names
    assert "_authorization_key" not in names
    assert not hasattr(client, "_custody")


def test_snapshot_mutation_does_not_change_authoritative_state(authority):
    client, _, _, _, _ = authority
    _registered(client)
    _ingest(client)
    snap = client.get_snapshot("pkg-1")["snapshot"]
    snap["closed"] = True
    snap["evidence"].clear()
    fresh = client.get_snapshot("pkg-1")["snapshot"]
    assert not fresh["closed"] and len(fresh["evidence"]) == 1


def test_post_closure_ingest_rejected(authority):
    client, _, _, _, _ = authority
    _registered(client)
    _ingest(client)
    assert client.close_package("pkg-1")["ok"]
    response = client.ingest_evidence(
        package_id="pkg-1",
        evidence_id="e-2",
        evidence_type="TEST",
        version=2,
        baseline_id="base-1",
        record={"late": True},
    )
    assert response["error"] == "package_closed"


def test_one_shot_registration_is_service_owned(authority):
    client, _, _, _, _ = authority
    first = client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="register-1",
    )
    assert first == client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="register-1",
    )
    assert not client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-2",
    )["ok"]


def test_request_id_reuse_with_different_payload_is_rejected(authority):
    client, _, _, _, _ = authority
    assert client.register_package(
        package_id="pkg-1",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="same-id",
    )["ok"]
    second = client.register_package(
        package_id="pkg-2",
        authority_required="CRE1AWS",
        required_evidence_types=[],
        baseline_id="base-1",
        request_id="same-id",
    )
    assert second["error"] == "request_id_reuse_mismatch"


def test_peer_allowlist_blocks_other_uids(tmp_path: Path):
    store = AuthorityStore(
        str(tmp_path / "store.sqlite3"),
        os.urandom(32),
        allowed_client_uid=1001,
        provenance_key=os.urandom(32),
    )
    try:
        request = {"schema": SCHEMA_VERSION, "request_id": "peer-bound", "operation": "health", "payload": {}}
        assert store.handle(request, 1001)["ok"]
        assert store.handle(request, 1002)["error"] == "peer_not_authorized"
    finally:
        store.close()


def test_client_rejects_unexpected_authority_uid(authority):
    _, _, socket_path, _, _ = authority
    impostor_check = CustodyClient(str(socket_path), expected_authority_uid=os.getuid() + 1)
    with pytest.raises(AuthorityUnavailable, match="identity mismatch"):
        impostor_check.health()


def test_production_server_rejects_same_uid(tmp_path: Path):
    auth = tmp_path / "a.key"
    prov = tmp_path / "p.key"
    _write_key(auth, os.urandom(32))
    _write_key(prov, os.urandom(32))
    with pytest.raises(ValueError, match="must be distinct"):
        AuthorityServer(
            str(tmp_path / "a.sock"),
            str(tmp_path / "a.sqlite3"),
            str(auth),
            str(prov),
            allowed_client_uid=os.getuid(),
        )


def test_authorization_and_provenance_keys_must_be_distinct(tmp_path: Path):
    key = os.urandom(32)
    with pytest.raises(ValueError, match="must be distinct"):
        AuthorityStore(
            str(tmp_path / "same-key.sqlite3"),
            key,
            allowed_client_uid=1001,
            provenance_key=key,
        )


def test_populated_database_without_continuity_metadata_fails_closed(tmp_path: Path):
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE packages(package_id TEXT PRIMARY KEY, authority_required TEXT NOT NULL, required_types TEXT NOT NULL, baseline_id TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO packages(package_id, authority_required, required_types, baseline_id, closed) VALUES('legacy','CRE1AWS','[]','b',0)"
    )
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="continuity metadata missing"):
        AuthorityStore(
            str(db),
            os.urandom(32),
            allowed_client_uid=1001,
            provenance_key=os.urandom(32),
        )


def test_unknown_generic_sign_operation_is_rejected(authority):
    client, _, _, _, _ = authority
    assert client._request("sign", {"payload": "forged"})["error"] == "unknown_operation"


def test_resolution_requires_scoped_external_capability(authority):
    client, _, _, auth_key, _ = authority
    _registered(client)
    client.open_issue(package_id="pkg-1", issue="REVIEW_REQUIRED")
    denied = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
        authorization={},
    )
    assert denied["error"] == "resolution_authorization_required"
    auth = _authorization(auth_key)
    resolved = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
        authorization=auth,
    )
    assert resolved["ok"]
    assert resolved["snapshot"]["resolutions"][0]["tag"].startswith("hmac-sha256:")


def test_resolution_capability_is_scope_bound_and_one_use(authority):
    client, _, _, auth_key, _ = authority
    _registered(client)
    client.open_issue(package_id="pkg-1", issue="REVIEW_REQUIRED")
    auth = _authorization(auth_key)
    mismatch = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="changed",
        authorization=auth,
    )
    assert mismatch["error"] == "resolution_authorization_scope_mismatch"
    ok = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
        authorization=auth,
    )
    assert ok["ok"]
    replay = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
        authorization=auth,
    )
    assert replay["error"] == "resolution_authorization_replayed"


def test_failed_transition_does_not_consume_authorization(authority):
    client, _, _, auth_key, _ = authority
    _registered(client)
    client.open_issue(package_id="pkg-1", issue="REVIEW_REQUIRED")
    auth = _authorization(auth_key, role="WRONG")
    kwargs = dict(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="WRONG",
        rationale="synthetic test authorization",
        authorization=auth,
    )
    assert client.resolve_issue(**kwargs)["error"] == "authority_role_mismatch"
    assert client.resolve_issue(**kwargs)["error"] == "authority_role_mismatch"


def test_expired_resolution_capability_is_rejected(authority):
    client, _, _, auth_key, _ = authority
    _registered(client)
    client.open_issue(package_id="pkg-1", issue="REVIEW_REQUIRED")
    auth = _authorization(auth_key, expires_at=int(time.time()) - 1)
    response = client.resolve_issue(
        package_id="pkg-1",
        issue="REVIEW_REQUIRED",
        actor="operator",
        role="CRE1AWS",
        rationale="synthetic test authorization",
        authorization=auth,
    )
    assert response["error"] == "resolution_authorization_expired"


def test_audit_snapshot_is_detached_and_chained(authority):
    client, _, _, _, _ = authority
    _registered(client)
    response = client.get_audit(limit=20)
    assert response["ok"]
    audit = list(reversed(response["audit"]))
    assert audit
    previous = "GENESIS"
    for row in audit:
        assert row["previous_tag"] == previous
        assert str(row["tag"]).startswith("hmac-sha256:")
        previous = row["tag"]
    audit[-1]["detail"] = "forged"
    fresh = client.get_audit(limit=20)["audit"]
    assert all(row["detail"] != "forged" for row in fresh)


def test_authority_unavailable_fails_closed(tmp_path: Path):
    with pytest.raises(AuthorityUnavailable):
        CustodyClient(
            str(tmp_path / "missing.sock"),
            expected_authority_uid=os.getuid(),
            timeout_seconds=0.1,
        ).health()


def test_client_functions_do_not_capture_service_store(authority):
    client, _, _, _, _ = authority
    for _, member in inspect.getmembers(client.__class__, predicate=inspect.isfunction):
        assert all(
            value.__class__.__name__ != "AuthorityStore"
            for value in [cell.cell_contents for cell in (member.__closure__ or ())]
        )


def test_schema_mismatch_fails_closed(authority):
    client, _, _, _, _ = authority
    original = client_module.SCHEMA_VERSION
    client_module.SCHEMA_VERSION = "BAD-SCHEMA"
    try:
        with pytest.raises(AuthorityUnavailable, match="schema mismatch"):
            client.health()
    finally:
        client_module.SCHEMA_VERSION = original


def test_wrong_restart_key_fails_closed(tmp_path: Path):
    db_path = tmp_path / "key-continuity.sqlite3"
    auth_key = os.urandom(32)
    provenance_key = os.urandom(32)
    store = AuthorityStore(
        str(db_path),
        auth_key,
        allowed_client_uid=1001,
        provenance_key=provenance_key,
    )
    store.close()
    with pytest.raises(RuntimeError, match="key continuity"):
        AuthorityStore(
            str(db_path),
            os.urandom(32),
            allowed_client_uid=1001,
            provenance_key=provenance_key,
        )
    with pytest.raises(RuntimeError, match="key continuity"):
        AuthorityStore(
            str(db_path),
            auth_key,
            allowed_client_uid=1001,
            provenance_key=os.urandom(32),
        )


def test_service_restart_preserves_resolution_chain_key(tmp_path: Path):
    auth_key = os.urandom(32)
    provenance_key = os.urandom(32)
    first, client, socket_path, _ = _start(tmp_path, auth_key, provenance_key)
    try:
        _registered(client, "pkg-r", required=())
        client.open_issue(package_id="pkg-r", issue="REVIEW_REQUIRED")
        auth = _authorization(auth_key, package_id="pkg-r")
        assert client.resolve_issue(
            package_id="pkg-r",
            issue="REVIEW_REQUIRED",
            actor="operator",
            role="CRE1AWS",
            rationale="synthetic test authorization",
            authorization=auth,
        )["ok"]
    finally:
        first.terminate()
        first.wait(timeout=5)
        if socket_path.exists():
            socket_path.unlink()
    second, client2, _, _ = _start(tmp_path, auth_key, provenance_key)
    try:
        snap = client2.get_snapshot("pkg-r")["snapshot"]
        assert len(snap["resolutions"]) == 1
        assert client2.close_package("pkg-r")["ok"]
    finally:
        second.terminate()
        second.wait(timeout=5)
