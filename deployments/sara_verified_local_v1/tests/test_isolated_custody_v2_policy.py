from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from worldshepherd_sara.isolated_custody_service_v2 import AuthorityStoreV2, CAP_SCHEMA, SCHEMA_VERSION


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _cap(key: bytes, operation: str, **bound):
    core = {
        "token_id": str(uuid.uuid4()),
        "operation": operation,
        "expires_at": int(time.time() + 300),
        **bound,
    }
    tag = "hmac-sha256:" + hmac.new(
        key,
        _canonical({"schema": CAP_SCHEMA, **core}),
        hashlib.sha256,
    ).hexdigest()
    return {"schema": CAP_SCHEMA, **core, "tag": tag}


def _request(operation, payload, request_id=None):
    return {
        "schema": SCHEMA_VERSION,
        "request_id": request_id or str(uuid.uuid4()),
        "operation": operation,
        "payload": payload,
    }


def _store(tmp_path):
    auth = os.urandom(32)
    provenance = os.urandom(32)
    store = AuthorityStoreV2(
        str(tmp_path / "authority-v2.sqlite3"),
        auth,
        provenance,
        allowed_client_uid=os.getuid(),
    )
    return store, auth


def _register(store, auth_key, peer_uid, package_id="pkg-1"):
    required = ["TEST"]
    bound = {
        "package_id": package_id,
        "authority_required": "CRE1AWS",
        "required_evidence_types": required,
        "baseline_id": "base-1",
    }
    payload = {**bound, "authorization": _cap(auth_key, "register_package", **bound)}
    response = store.handle(_request("register_package", payload), peer_uid)
    assert response["ok"]


def test_registration_requires_independent_scoped_capability(tmp_path):
    store, auth = _store(tmp_path)
    try:
        payload = {
            "package_id": "pkg-1",
            "authority_required": "CRE1AWS",
            "required_evidence_types": ["TEST"],
            "baseline_id": "base-1",
        }
        denied = store.handle(_request("register_package", payload), os.getuid())
        assert denied["error"] == "register_package_authorization_required"
        bound = dict(payload)
        payload["authorization"] = _cap(auth, "register_package", **bound)
        assert store.handle(_request("register_package", payload), os.getuid())["ok"]
    finally:
        store.close()


def test_registration_rejects_client_selected_empty_evidence_policy_even_if_signed(tmp_path):
    store, auth = _store(tmp_path)
    try:
        bound = {
            "package_id": "pkg-empty",
            "authority_required": "CRE1AWS",
            "required_evidence_types": [],
            "baseline_id": "base-1",
        }
        payload = {**bound, "authorization": _cap(auth, "register_package", **bound)}
        response = store.handle(_request("register_package", payload), os.getuid())
        assert response["error"] == "required_evidence_types_must_not_be_empty"
    finally:
        store.close()


def test_evidence_requires_attestation_bound_to_payload_source_version_and_chain(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        record = {"measurement": 7, "source": "synthetic-fixture"}
        digest = hashlib.sha256(_canonical(record)).hexdigest()
        bound = {
            "package_id": "pkg-1",
            "evidence_id": "e-1",
            "evidence_type": "TEST",
            "version": 1,
            "baseline_id": "base-1",
            "source_id": "fixture-source",
            "previous_digest": "GENESIS",
            "digest": digest,
        }
        denied = store.handle(_request("ingest_evidence", {**bound, "record": record}), os.getuid())
        assert denied["error"] == "ingest_evidence_authorization_required"
        forged_record = {"measurement": 999, "source": "forged"}
        payload = {**bound, "record": forged_record, "authorization": _cap(auth, "ingest_evidence", **bound)}
        mismatch = store.handle(_request("ingest_evidence", payload), os.getuid())
        assert mismatch["error"] == "ingest_evidence_authorization_scope_mismatch"
    finally:
        store.close()


def test_closure_revalidates_stored_payload_and_authority_attestation(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        record = {"measurement": 7, "source": "validated-fixture"}
        digest = hashlib.sha256(_canonical(record)).hexdigest()
        bound = {
            "package_id": "pkg-1",
            "evidence_id": "e-1",
            "evidence_type": "TEST",
            "version": 1,
            "baseline_id": "base-1",
            "source_id": "fixture-source",
            "previous_digest": "GENESIS",
            "digest": digest,
        }
        payload = {**bound, "record": record, "authorization": _cap(auth, "ingest_evidence", **bound)}
        assert store.handle(_request("ingest_evidence", payload), os.getuid())["ok"]
        store._db.execute("UPDATE evidence SET payload=? WHERE package_id=? AND evidence_id=?", (json.dumps({"forged": True}), "pkg-1", "e-1"))
        store._db.commit()
        bound_close = {"package_id": "pkg-1"}
        closed = store.handle(
            _request("close_package", {**bound_close, "authorization": _cap(auth, "close_package", **bound_close)}),
            os.getuid(),
        )
        assert closed["error"] == "evidence_payload_integrity_failure"
    finally:
        store.close()


def test_closure_rejects_unattested_required_type_even_if_database_row_exists(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        record = {"measurement": 7}
        digest = hashlib.sha256(_canonical(record)).hexdigest()
        store._db.execute(
            "INSERT INTO evidence(package_id,evidence_id,evidence_type,version,baseline_id,source_id,previous_digest,digest,payload,attestation_tag) VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("pkg-1", "evil", "TEST", 1, "base-1", "evil-source", "GENESIS", digest, json.dumps(record, sort_keys=True), "hmac-sha256:forged"),
        )
        store._db.commit()
        bound_close = {"package_id": "pkg-1"}
        closed = store.handle(
            _request("close_package", {**bound_close, "authorization": _cap(auth, "close_package", **bound_close)}),
            os.getuid(),
        )
        assert closed["error"] == "evidence_attestation_failure"
    finally:
        store.close()


def test_issue_creation_requires_scoped_capability(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        denied = store.handle(
            _request("open_issue", {"package_id": "pkg-1", "issue": "REVIEW_REQUIRED"}),
            os.getuid(),
        )
        assert denied["error"] == "open_issue_authorization_required"
        bound = {"package_id": "pkg-1", "issue": "REVIEW_REQUIRED"}
        authorized = store.handle(
            _request("open_issue", {**bound, "authorization": _cap(auth, "open_issue", **bound)}),
            os.getuid(),
        )
        assert authorized["ok"]
        assert authorized["snapshot"]["open_issues"] == ["REVIEW_REQUIRED"]
    finally:
        store.close()


def test_closure_requires_scoped_capability(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        denied = store.handle(_request("close_package", {"package_id": "pkg-1"}), os.getuid())
        assert denied["error"] == "close_package_authorization_required"
        bound = {"package_id": "pkg-1"}
        authorized = store.handle(
            _request("close_package", {**bound, "authorization": _cap(auth, "close_package", **bound)}),
            os.getuid(),
        )
        assert authorized["error"].startswith("missing_validated_evidence:")
    finally:
        store.close()


def test_incomplete_socket_request_is_time_bounded(tmp_path):
    socket_path = tmp_path / "authority-v2.sock"
    db_path = tmp_path / "authority-v2.sqlite3"
    auth_path = tmp_path / "authorization.key"
    provenance_path = tmp_path / "provenance.key"
    auth_path.write_bytes(os.urandom(32))
    provenance_path.write_bytes(os.urandom(32))
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "worldshepherd_sara.isolated_custody_service_v2",
            "--socket",
            str(socket_path),
            "--db",
            str(db_path),
            "--authorization-key-file",
            str(auth_path),
            "--provenance-key-file",
            str(provenance_path),
            "--allowed-client-uid",
            str(os.getuid() + 1),
            "--connection-timeout-seconds",
            "0.05",
        ],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not socket_path.exists():
            time.sleep(0.01)
        assert socket_path.exists()
        slow = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        slow.settimeout(1)
        started = time.monotonic()
        slow.connect(str(socket_path))
        for _ in range(20):
            try:
                slow.sendall(b"{")
            except BrokenPipeError:
                break
            time.sleep(0.01)
        response = slow.recv(65536)
        elapsed = time.monotonic() - started
        assert elapsed < 0.75
        assert b'"error": "invalid_request"' in response
        slow.close()
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_idempotent_close_consumes_one_use_capability(tmp_path):
    store, auth = _store(tmp_path)
    try:
        _register(store, auth, os.getuid())
        store._db.execute("UPDATE packages SET closed=1 WHERE package_id=?", ("pkg-1",))
        store._db.commit()
        bound = {"package_id": "pkg-1"}
        capability = _cap(auth, "close_package", **bound)
        first = store.handle(
            _request("close_package", {**bound, "authorization": capability}),
            os.getuid(),
        )
        assert first["ok"]
        replay = store.handle(
            _request("close_package", {**bound, "authorization": capability}),
            os.getuid(),
        )
        assert replay["error"] == "close_package_authorization_replayed"
    finally:
        store.close()
