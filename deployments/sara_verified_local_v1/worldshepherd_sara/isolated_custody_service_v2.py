from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import socket
import sqlite3
import struct
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "WS-SENTINEL-CUSTODY-V2"
CAP_SCHEMA = "WS-SENTINEL-CAPABILITY-V2"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_once_secret(path: str) -> bytes:
    p = Path(path)
    value = p.read_bytes()
    if len(value) < 32:
        raise ValueError("authority secret must be at least 32 bytes")
    p.unlink()
    return value


def _hmac(key: bytes, value: Any) -> str:
    return "hmac-sha256:" + hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()


class AuthorityStoreV2:
    """Isolated authority. Client requests are untrusted until capability/policy validation succeeds."""

    def __init__(self, db_path: str, authorization_key: bytes, provenance_key: bytes, *, allowed_client_uid: int):
        if hmac.compare_digest(authorization_key, provenance_key):
            raise ValueError("authorization and provenance keys must be distinct")
        self._authorization_key = bytes(authorization_key)
        self._provenance_key = bytes(provenance_key)
        self._allowed_client_uid = int(allowed_client_uid)
        self._db = sqlite3.connect(db_path)
        self._db.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(name TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS packages(
                package_id TEXT PRIMARY KEY,
                authority_required TEXT NOT NULL,
                required_types TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                closed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS evidence(
                package_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                version INTEGER NOT NULL,
                baseline_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                previous_digest TEXT NOT NULL,
                digest TEXT NOT NULL,
                payload TEXT NOT NULL,
                attestation_tag TEXT NOT NULL,
                PRIMARY KEY(package_id, evidence_id),
                UNIQUE(package_id, evidence_type, version)
            );
            CREATE TABLE IF NOT EXISTS issues(
                package_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                open INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(package_id, issue)
            );
            CREATE TABLE IF NOT EXISTS resolutions(
                package_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                issue TEXT NOT NULL,
                actor TEXT NOT NULL,
                role TEXT NOT NULL,
                rationale TEXT NOT NULL,
                previous_tag TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY(package_id, seq)
            );
            CREATE TABLE IF NOT EXISTS used_capabilities(
                token_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                package_id TEXT NOT NULL,
                used_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS requests(
                request_id TEXT PRIMARY KEY,
                peer_uid INTEGER NOT NULL,
                request_digest TEXT NOT NULL,
                response_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                peer_uid INTEGER NOT NULL,
                operation TEXT NOT NULL,
                accepted INTEGER NOT NULL,
                detail TEXT NOT NULL,
                previous_tag TEXT NOT NULL,
                tag TEXT NOT NULL
            );
            """
        )
        populated = any(
            self._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("packages", "evidence", "issues", "resolutions", "used_capabilities", "requests", "audit")
        )
        expected = {
            "schema_version": SCHEMA_VERSION,
            "authorization_key_check": _hmac(self._authorization_key, {"purpose": "authorization-continuity-v2"}),
            "provenance_key_check": _hmac(self._provenance_key, {"purpose": "provenance-continuity-v2"}),
        }
        for name, value in expected.items():
            row = self._db.execute("SELECT value FROM meta WHERE name=?", (name,)).fetchone()
            if row is None:
                if populated:
                    raise RuntimeError("v2 continuity metadata missing for populated database")
                self._db.execute("INSERT INTO meta(name,value) VALUES(?,?)", (name, value))
            elif not hmac.compare_digest(str(row["value"]), value):
                raise RuntimeError("v2 authority continuity check failed")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def _verify_capability(self, operation: str, payload: dict[str, Any], bound: dict[str, Any]) -> dict[str, Any]:
        cap = payload.get("authorization")
        if not isinstance(cap, dict) or cap.get("schema") != CAP_SCHEMA:
            raise ValueError(f"{operation}_authorization_required")
        core = {
            "token_id": str(cap.get("token_id", "")),
            "operation": str(cap.get("operation", "")),
            "expires_at": int(cap.get("expires_at", 0)),
            **bound,
        }
        if not core["token_id"] or core["operation"] != operation:
            raise ValueError(f"invalid_{operation}_authorization")
        for field, expected in bound.items():
            if cap.get(field) != expected:
                raise ValueError(f"{operation}_authorization_scope_mismatch")
        if core["expires_at"] < int(time.time()):
            raise ValueError(f"{operation}_authorization_expired")
        expected_tag = _hmac(self._authorization_key, {"schema": CAP_SCHEMA, **core})
        if not hmac.compare_digest(str(cap.get("tag", "")), expected_tag):
            raise ValueError(f"invalid_{operation}_authorization")
        if self._db.execute("SELECT 1 FROM used_capabilities WHERE token_id=?", (core["token_id"],)).fetchone():
            raise ValueError(f"{operation}_authorization_replayed")
        return core

    def _consume(self, cap: dict[str, Any], package_id: str) -> None:
        self._db.execute(
            "INSERT INTO used_capabilities(token_id,operation,package_id,used_at) VALUES(?,?,?,?)",
            (cap["token_id"], cap["operation"], package_id, int(time.time())),
        )

    def _audit(self, request_id: str, peer_uid: int, operation: str, accepted: bool, detail: str) -> None:
        prior = self._db.execute("SELECT tag FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = "GENESIS" if prior is None else str(prior["tag"])
        body = {
            "schema": "WS-SENTINEL-AUDIT-V2",
            "request_id": request_id,
            "peer_uid": peer_uid,
            "operation": operation,
            "accepted": bool(accepted),
            "detail": detail,
            "previous_tag": previous,
        }
        tag = _hmac(self._provenance_key, body)
        self._db.execute(
            "INSERT INTO audit(request_id,peer_uid,operation,accepted,detail,previous_tag,tag) VALUES(?,?,?,?,?,?,?)",
            (request_id, peer_uid, operation, int(accepted), detail, previous, tag),
        )

    def _evidence_attestation(self, row: dict[str, Any]) -> str:
        body = {
            "schema": "WS-SENTINEL-EVIDENCE-ATTESTATION-V2",
            "package_id": row["package_id"],
            "evidence_id": row["evidence_id"],
            "evidence_type": row["evidence_type"],
            "version": int(row["version"]),
            "baseline_id": row["baseline_id"],
            "source_id": row["source_id"],
            "previous_digest": row["previous_digest"],
            "digest": row["digest"],
        }
        return _hmac(self._provenance_key, body)

    def _snapshot(self, package_id: str) -> dict[str, Any]:
        p = self._db.execute("SELECT * FROM packages WHERE package_id=?", (package_id,)).fetchone()
        if p is None:
            raise KeyError("unknown_package")
        evidence = [dict(r) for r in self._db.execute(
            "SELECT evidence_id,evidence_type,version,baseline_id,source_id,previous_digest,digest,attestation_tag FROM evidence WHERE package_id=? ORDER BY evidence_type,version",
            (package_id,),
        )]
        issues = [r["issue"] for r in self._db.execute("SELECT issue FROM issues WHERE package_id=? AND open=1", (package_id,))]
        return {
            "package_id": p["package_id"],
            "authority_required": p["authority_required"],
            "required_evidence_types": json.loads(p["required_types"]),
            "baseline_id": p["baseline_id"],
            "closed": bool(p["closed"]),
            "evidence": evidence,
            "open_issues": issues,
        }

    def _validate_authoritative_evidence(self, package_id: str, baseline_id: str) -> set[str]:
        rows = [dict(r) for r in self._db.execute(
            "SELECT * FROM evidence WHERE package_id=? ORDER BY evidence_type,version", (package_id,)
        )]
        latest: dict[str, dict[str, Any]] = {}
        chain_tip: dict[str, str] = {}
        last_version: dict[str, int] = {}
        for row in rows:
            if row["baseline_id"] != baseline_id or not row["source_id"]:
                raise ValueError("invalid_authoritative_evidence")
            payload = json.loads(row["payload"])
            digest = hashlib.sha256(_canonical(payload)).hexdigest()
            if digest != row["digest"]:
                raise ValueError("evidence_payload_integrity_failure")
            expected_previous = chain_tip.get(row["evidence_type"], "GENESIS")
            if row["previous_digest"] != expected_previous:
                raise ValueError("evidence_chain_failure")
            if int(row["version"]) <= last_version.get(row["evidence_type"], 0):
                raise ValueError("evidence_version_failure")
            if not hmac.compare_digest(row["attestation_tag"], self._evidence_attestation(row)):
                raise ValueError("evidence_attestation_failure")
            chain_tip[row["evidence_type"]] = row["digest"]
            last_version[row["evidence_type"]] = int(row["version"])
            latest[row["evidence_type"]] = row
        return set(latest)

    def handle(self, request: dict[str, Any], peer_uid: int) -> dict[str, Any]:
        request_id = str(request.get("request_id", ""))
        operation = str(request.get("operation", ""))
        if request.get("schema") != SCHEMA_VERSION:
            return {"ok": False, "error": "schema_mismatch", "schema": SCHEMA_VERSION}
        if not request_id:
            return {"ok": False, "error": "request_id_required", "schema": SCHEMA_VERSION}
        if peer_uid != self._allowed_client_uid:
            self._audit(request_id, peer_uid, operation, False, "peer_not_authorized")
            self._db.commit()
            return {"ok": False, "error": "peer_not_authorized", "schema": SCHEMA_VERSION}
        digest = hashlib.sha256(_canonical(request)).hexdigest()
        prior = self._db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if prior is not None:
            if int(prior["peer_uid"]) != peer_uid:
                return {"ok": False, "error": "request_peer_mismatch", "schema": SCHEMA_VERSION}
            if prior["request_digest"] != digest:
                return {"ok": False, "error": "request_id_reuse_mismatch", "schema": SCHEMA_VERSION}
            return json.loads(prior["response_json"])
        self._db.execute("SAVEPOINT transition")
        try:
            response = self._dispatch(operation, request.get("payload") or {})
        except (KeyError, ValueError) as exc:
            self._db.execute("ROLLBACK TO transition")
            response = {"ok": False, "error": str(exc.args[0] if isinstance(exc, KeyError) else exc), "schema": SCHEMA_VERSION}
        except sqlite3.IntegrityError:
            self._db.execute("ROLLBACK TO transition")
            response = {"ok": False, "error": "conflict", "schema": SCHEMA_VERSION}
        finally:
            self._db.execute("RELEASE transition")
        self._audit(request_id, peer_uid, operation, bool(response.get("ok")), str(response.get("error") or "accepted"))
        self._db.execute(
            "INSERT INTO requests(request_id,peer_uid,request_digest,response_json) VALUES(?,?,?,?)",
            (request_id, peer_uid, digest, json.dumps(response, sort_keys=True)),
        )
        self._db.commit()
        return response

    def _dispatch(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation == "health":
            return {"ok": True, "schema": SCHEMA_VERSION, "status": "ready"}
        if operation == "get_snapshot":
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(str(payload["package_id"]))}
        if operation == "register_package":
            package_id = str(payload["package_id"])
            required = sorted(set(str(x) for x in payload.get("required_evidence_types") or []))
            if not required:
                raise ValueError("required_evidence_types_must_not_be_empty")
            bound = {
                "package_id": package_id,
                "authority_required": str(payload["authority_required"]),
                "required_evidence_types": required,
                "baseline_id": str(payload["baseline_id"]),
            }
            cap = self._verify_capability("register_package", payload, bound)
            self._consume(cap, package_id)
            self._db.execute(
                "INSERT INTO packages(package_id,authority_required,required_types,baseline_id,closed) VALUES(?,?,?,?,0)",
                (package_id, bound["authority_required"], json.dumps(required), bound["baseline_id"]),
            )
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "ingest_evidence":
            package_id = str(payload["package_id"])
            package = self._db.execute("SELECT * FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                raise ValueError("package_closed")
            record = payload.get("record")
            if not isinstance(record, dict):
                raise ValueError("evidence_record_required")
            digest = hashlib.sha256(_canonical(record)).hexdigest()
            evidence_type = str(payload["evidence_type"])
            version = int(payload["version"])
            prior = self._db.execute(
                "SELECT version,digest FROM evidence WHERE package_id=? AND evidence_type=? ORDER BY version DESC LIMIT 1",
                (package_id, evidence_type),
            ).fetchone()
            expected_previous = "GENESIS" if prior is None else str(prior["digest"])
            if prior is not None and version <= int(prior["version"]):
                raise ValueError("evidence_version_not_monotonic")
            bound = {
                "package_id": package_id,
                "evidence_id": str(payload["evidence_id"]),
                "evidence_type": evidence_type,
                "version": version,
                "baseline_id": str(payload["baseline_id"]),
                "source_id": str(payload.get("source_id", "")),
                "previous_digest": str(payload.get("previous_digest", "")),
                "digest": digest,
            }
            if bound["baseline_id"] != package["baseline_id"]:
                raise ValueError("stale_baseline")
            if not bound["source_id"]:
                raise ValueError("evidence_source_required")
            if bound["previous_digest"] != expected_previous:
                raise ValueError("evidence_previous_digest_mismatch")
            cap = self._verify_capability("ingest_evidence", payload, bound)
            row = {**bound, "payload": json.dumps(record, sort_keys=True)}
            attestation = self._evidence_attestation(row)
            self._consume(cap, package_id)
            self._db.execute(
                "INSERT INTO evidence(package_id,evidence_id,evidence_type,version,baseline_id,source_id,previous_digest,digest,payload,attestation_tag) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (package_id, bound["evidence_id"], evidence_type, version, bound["baseline_id"], bound["source_id"], bound["previous_digest"], digest, row["payload"], attestation),
            )
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "open_issue":
            package_id = str(payload["package_id"])
            issue = str(payload["issue"])
            package = self._db.execute("SELECT closed FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                raise ValueError("package_closed")
            bound = {"package_id": package_id, "issue": issue}
            cap = self._verify_capability("open_issue", payload, bound)
            self._consume(cap, package_id)
            self._db.execute("INSERT INTO issues(package_id,issue,open) VALUES(?,?,1)", (package_id, issue))
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "close_package":
            package_id = str(payload["package_id"])
            package = self._db.execute("SELECT * FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            bound = {"package_id": package_id}
            cap = self._verify_capability("close_package", payload, bound)
            if package["closed"]:
                return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
            required = set(json.loads(package["required_types"]))
            valid_types = self._validate_authoritative_evidence(package_id, str(package["baseline_id"]))
            missing = sorted(required - valid_types)
            if missing:
                raise ValueError("missing_validated_evidence:" + ",".join(missing))
            open_issues = self._db.execute("SELECT COUNT(*) n FROM issues WHERE package_id=? AND open=1", (package_id,)).fetchone()["n"]
            if open_issues:
                raise ValueError("unresolved_issues")
            self._consume(cap, package_id)
            self._db.execute("UPDATE packages SET closed=1 WHERE package_id=?", (package_id,))
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        raise ValueError("unknown_operation")


class AuthorityServerV2:
    def __init__(self, socket_path: str, db_path: str, authorization_key_file: str, provenance_key_file: str, *, allowed_client_uid: int, socket_mode: int = 0o600, connection_timeout_seconds: float = 1.0):
        if int(allowed_client_uid) == os.getuid():
            raise ValueError("authority and client UIDs must be distinct")
        self._socket_path = socket_path
        self._socket_mode = socket_mode
        self._connection_timeout_seconds = max(0.05, float(connection_timeout_seconds))
        self._store = AuthorityStoreV2(
            db_path,
            _read_once_secret(authorization_key_file),
            _read_once_secret(provenance_key_file),
            allowed_client_uid=allowed_client_uid,
        )

    def serve_forever(self) -> None:
        path = Path(self._socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self._socket_path)
        os.chmod(self._socket_path, self._socket_mode)
        server.listen(16)
        try:
            while True:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(self._connection_timeout_seconds)
                    peer_uid = -1
                    if hasattr(socket, "SO_PEERCRED"):
                        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
                        _pid, peer_uid, _gid = struct.unpack("3i", raw)
                    data = b""
                    while not data.endswith(b"\n") and len(data) <= 2_000_000:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    try:
                        response = self._store.handle(json.loads(data.decode("utf-8")), peer_uid)
                    except Exception as exc:
                        response = {"ok": False, "error": "invalid_request", "detail": type(exc).__name__, "schema": SCHEMA_VERSION}
                    conn.sendall(json.dumps(response, sort_keys=True).encode("utf-8") + b"\n")
        finally:
            server.close()
            self._store.close()
            if path.exists():
                path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--authorization-key-file", required=True)
    parser.add_argument("--provenance-key-file", required=True)
    parser.add_argument("--allowed-client-uid", type=int, required=True)
    parser.add_argument("--socket-mode", type=lambda v: int(v, 8), default=0o600)
    parser.add_argument("--connection-timeout-seconds", type=float, default=1.0)
    args = parser.parse_args()
    AuthorityServerV2(
        args.socket,
        args.db,
        args.authorization_key_file,
        args.provenance_key_file,
        allowed_client_uid=args.allowed_client_uid,
        socket_mode=args.socket_mode,
        connection_timeout_seconds=args.connection_timeout_seconds,
    ).serve_forever()


if __name__ == "__main__":
    main()
