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

SCHEMA_VERSION = "WS-SENTINEL-CUSTODY-V1"
AUTH_SCHEMA = "WS-SENTINEL-RESOLUTION-AUTH-V1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_once_secret(path: str) -> bytes:
    secret_path = Path(path)
    value = secret_path.read_bytes()
    if len(value) < 32:
        raise ValueError("authority secret must be at least 32 bytes")
    secret_path.unlink()
    return value


class AuthorityStore:
    """Authoritative state owned only by the isolated authority process."""

    def __init__(self, db_path: str, authorization_key: bytes, allowed_client_uid: int | None = None):
        self._db_path = db_path
        self._authorization_key = bytes(authorization_key)
        self._allowed_client_uid = os.getuid() if allowed_client_uid is None else int(allowed_client_uid)
        self._resolution_key = hmac.new(
            self._authorization_key,
            b"WS-SENTINEL-RESOLUTION-PROVENANCE-KEY-V1",
            hashlib.sha256,
        ).digest()
        self._audit_key = hmac.new(
            self._authorization_key,
            b"WS-SENTINEL-AUDIT-PROVENANCE-KEY-V1",
            hashlib.sha256,
        ).digest()
        self._db = sqlite3.connect(db_path)
        self._db.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS packages (
                package_id TEXT PRIMARY KEY,
                authority_required TEXT NOT NULL,
                required_types TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                closed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS evidence (
                package_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                version INTEGER NOT NULL,
                baseline_id TEXT NOT NULL,
                digest TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (package_id, evidence_id)
            );
            CREATE TABLE IF NOT EXISTS issues (
                package_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                open INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (package_id, issue)
            );
            CREATE TABLE IF NOT EXISTS resolutions (
                package_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                issue TEXT NOT NULL,
                actor TEXT NOT NULL,
                role TEXT NOT NULL,
                rationale TEXT NOT NULL,
                previous_tag TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (package_id, seq)
            );
            CREATE TABLE IF NOT EXISTS requests (
                request_id TEXT PRIMARY KEY,
                peer_uid INTEGER NOT NULL,
                request_digest TEXT NOT NULL,
                response_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS used_authorizations (
                token_id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                used_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                peer_uid INTEGER NOT NULL,
                operation TEXT NOT NULL,
                accepted INTEGER NOT NULL,
                detail TEXT NOT NULL,
                previous_tag TEXT NOT NULL DEFAULT 'GENESIS',
                tag TEXT NOT NULL DEFAULT ''
            );
            """
        )
        request_columns = {row["name"] for row in self._db.execute("PRAGMA table_info(requests)")}
        if "peer_uid" not in request_columns:
            self._db.execute("ALTER TABLE requests ADD COLUMN peer_uid INTEGER NOT NULL DEFAULT -1")
        audit_columns = {row["name"] for row in self._db.execute("PRAGMA table_info(audit)")}
        if "previous_tag" not in audit_columns:
            self._db.execute("ALTER TABLE audit ADD COLUMN previous_tag TEXT NOT NULL DEFAULT 'GENESIS'")
        if "tag" not in audit_columns:
            self._db.execute("ALTER TABLE audit ADD COLUMN tag TEXT NOT NULL DEFAULT ''")

        key_check = "hmac-sha256:" + hmac.new(
            self._authorization_key,
            b"WS-SENTINEL-AUTHORITY-KEY-CONTINUITY-V1",
            hashlib.sha256,
        ).hexdigest()
        row = self._db.execute("SELECT value FROM meta WHERE name='authority_key_check'").fetchone()
        if row is None:
            self._db.execute("INSERT INTO meta(name, value) VALUES('authority_key_check', ?)", (key_check,))
        elif not hmac.compare_digest(str(row["value"]), key_check):
            raise RuntimeError("authority key continuity check failed")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def _audit(self, request_id: str, peer_uid: int, operation: str, accepted: bool, detail: str) -> None:
        prior = self._db.execute("SELECT tag FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous_tag = "GENESIS" if prior is None or not prior["tag"] else str(prior["tag"])
        payload = {
            "schema": "WS-SENTINEL-AUDIT-CHAIN-V1",
            "request_id": request_id,
            "peer_uid": peer_uid,
            "operation": operation,
            "accepted": bool(accepted),
            "detail": detail,
            "previous_tag": previous_tag,
        }
        tag = "hmac-sha256:" + hmac.new(self._audit_key, _canonical(payload), hashlib.sha256).hexdigest()
        self._db.execute(
            "INSERT INTO audit(request_id, peer_uid, operation, accepted, detail, previous_tag, tag) VALUES(?,?,?,?,?,?,?)",
            (request_id, peer_uid, operation, int(accepted), detail, previous_tag, tag),
        )

    def _snapshot(self, package_id: str) -> dict[str, Any]:
        package = self._db.execute(
            "SELECT package_id, authority_required, required_types, baseline_id, closed FROM packages WHERE package_id=?",
            (package_id,),
        ).fetchone()
        if package is None:
            raise KeyError("unknown_package")
        evidence = [dict(row) for row in self._db.execute(
            "SELECT evidence_id, evidence_type, version, baseline_id, digest FROM evidence WHERE package_id=? ORDER BY evidence_type, version, evidence_id",
            (package_id,),
        )]
        issues = [row["issue"] for row in self._db.execute(
            "SELECT issue FROM issues WHERE package_id=? AND open=1 ORDER BY issue", (package_id,)
        )]
        resolutions = [dict(row) for row in self._db.execute(
            "SELECT seq, issue, actor, role, rationale, previous_tag, tag FROM resolutions WHERE package_id=? ORDER BY seq",
            (package_id,),
        )]
        return {
            "package_id": package["package_id"],
            "authority_required": package["authority_required"],
            "required_evidence_types": json.loads(package["required_types"]),
            "baseline_id": package["baseline_id"],
            "closed": bool(package["closed"]),
            "evidence": evidence,
            "open_issues": issues,
            "resolutions": resolutions,
        }

    def _audit_snapshot(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        return [dict(row) for row in self._db.execute(
            "SELECT seq, request_id, peer_uid, operation, accepted, detail, previous_tag, tag FROM audit ORDER BY seq DESC LIMIT ?",
            (safe_limit,),
        )]

    def _resolution_tag(self, package_id: str, seq: int, issue: str, actor: str, role: str, rationale: str, previous_tag: str) -> str:
        payload = {
            "schema": SCHEMA_VERSION,
            "package_id": package_id,
            "seq": seq,
            "issue": issue,
            "actor": actor,
            "role": role,
            "rationale": rationale,
            "previous_tag": previous_tag,
        }
        return "hmac-sha256:" + hmac.new(self._resolution_key, _canonical(payload), hashlib.sha256).hexdigest()

    def _verify_resolution_authorization(self, payload: dict[str, Any]) -> None:
        auth = payload.get("authorization")
        if not isinstance(auth, dict) or auth.get("schema") != AUTH_SCHEMA:
            raise ValueError("resolution_authorization_required")
        required = {
            "token_id": str(auth.get("token_id", "")),
            "operation": str(auth.get("operation", "")),
            "package_id": str(auth.get("package_id", "")),
            "issue": str(auth.get("issue", "")),
            "actor": str(auth.get("actor", "")),
            "role": str(auth.get("role", "")),
            "rationale": str(auth.get("rationale", "")),
            "expires_at": int(auth.get("expires_at", 0)),
        }
        if not required["token_id"] or required["operation"] != "resolve_issue":
            raise ValueError("invalid_resolution_authorization")
        for field in ("package_id", "issue", "actor", "role", "rationale"):
            if required[field] != str(payload.get(field, "")):
                raise ValueError("resolution_authorization_scope_mismatch")
        if required["expires_at"] < int(time.time()):
            raise ValueError("resolution_authorization_expired")
        expected = hmac.new(self._authorization_key, _canonical({"schema": AUTH_SCHEMA, **required}), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(auth.get("tag", "")), "hmac-sha256:" + expected):
            raise ValueError("invalid_resolution_authorization")
        if self._db.execute("SELECT 1 FROM used_authorizations WHERE token_id=?", (required["token_id"],)).fetchone():
            raise ValueError("resolution_authorization_replayed")
        self._db.execute(
            "INSERT INTO used_authorizations(token_id, package_id, issue, used_at) VALUES(?,?,?,?)",
            (required["token_id"], required["package_id"], required["issue"], int(time.time())),
        )

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
        prior = self._db.execute(
            "SELECT peer_uid, request_digest, response_json FROM requests WHERE request_id=?", (request_id,)
        ).fetchone()
        if prior is not None:
            if int(prior["peer_uid"]) != peer_uid:
                self._audit(request_id, peer_uid, operation, False, "request_peer_mismatch")
                self._db.commit()
                return {"ok": False, "error": "request_peer_mismatch", "schema": SCHEMA_VERSION}
            if prior["request_digest"] != digest:
                self._audit(request_id, peer_uid, operation, False, "request_id_reuse_mismatch")
                self._db.commit()
                return {"ok": False, "error": "request_id_reuse_mismatch", "schema": SCHEMA_VERSION}
            return json.loads(prior["response_json"])
        try:
            response = self._dispatch(operation, request.get("payload") or {})
        except KeyError as exc:
            response = {"ok": False, "error": str(exc.args[0]), "schema": SCHEMA_VERSION}
        except ValueError as exc:
            response = {"ok": False, "error": str(exc), "schema": SCHEMA_VERSION}
        except sqlite3.IntegrityError:
            response = {"ok": False, "error": "conflict", "schema": SCHEMA_VERSION}
        self._audit(request_id, peer_uid, operation, bool(response.get("ok")), str(response.get("error") or "accepted"))
        self._db.execute(
            "INSERT INTO requests(request_id, peer_uid, request_digest, response_json) VALUES(?,?,?,?)",
            (request_id, peer_uid, digest, json.dumps(response, sort_keys=True)),
        )
        self._db.commit()
        return response

    def _dispatch(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation == "health":
            tip = self._db.execute("SELECT tag FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            return {"ok": True, "schema": SCHEMA_VERSION, "status": "ready", "audit_tip": None if tip is None else tip["tag"]}
        if operation == "get_audit":
            return {"ok": True, "schema": SCHEMA_VERSION, "audit": self._audit_snapshot(int(payload.get("limit", 100)))}
        if operation == "register_package":
            package_id = str(payload["package_id"])
            self._db.execute(
                "INSERT INTO packages(package_id, authority_required, required_types, baseline_id, closed) VALUES(?,?,?,?,0)",
                (package_id, str(payload["authority_required"]), json.dumps(sorted(set(payload.get("required_evidence_types") or []))), str(payload["baseline_id"])),
            )
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "get_snapshot":
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(str(payload["package_id"]))}
        if operation == "ingest_evidence":
            package_id = str(payload["package_id"])
            package = self._db.execute("SELECT closed, baseline_id FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                raise ValueError("package_closed")
            if str(payload["baseline_id"]) != package["baseline_id"]:
                raise ValueError("stale_baseline")
            record_payload = payload.get("record") or {}
            record_digest = hashlib.sha256(_canonical(record_payload)).hexdigest()
            if payload.get("digest") != record_digest:
                raise ValueError("digest_mismatch")
            self._db.execute(
                "INSERT INTO evidence(package_id, evidence_id, evidence_type, version, baseline_id, digest, payload) VALUES(?,?,?,?,?,?,?)",
                (package_id, str(payload["evidence_id"]), str(payload["evidence_type"]), int(payload["version"]), str(payload["baseline_id"]), record_digest, json.dumps(record_payload, sort_keys=True)),
            )
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "open_issue":
            package_id = str(payload["package_id"])
            package = self._db.execute("SELECT closed FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                raise ValueError("package_closed")
            self._db.execute("INSERT INTO issues(package_id, issue, open) VALUES(?,?,1)", (package_id, str(payload["issue"])))
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "resolve_issue":
            package_id = str(payload["package_id"])
            self._verify_resolution_authorization(payload)
            package = self._db.execute("SELECT closed, authority_required FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                raise ValueError("package_closed")
            if str(payload["role"]) != package["authority_required"]:
                raise ValueError("authority_role_mismatch")
            issue = str(payload["issue"])
            issue_row = self._db.execute("SELECT open FROM issues WHERE package_id=? AND issue=?", (package_id, issue)).fetchone()
            if issue_row is None or not issue_row["open"]:
                raise ValueError("issue_not_open")
            rationale = str(payload.get("rationale") or "").strip()
            if not rationale:
                raise ValueError("rationale_required")
            prior = self._db.execute("SELECT seq, tag FROM resolutions WHERE package_id=? ORDER BY seq DESC LIMIT 1", (package_id,)).fetchone()
            seq = 1 if prior is None else int(prior["seq"]) + 1
            previous_tag = "GENESIS" if prior is None else str(prior["tag"])
            actor, role = str(payload["actor"]), str(payload["role"])
            tag = self._resolution_tag(package_id, seq, issue, actor, role, rationale, previous_tag)
            self._db.execute(
                "INSERT INTO resolutions(package_id, seq, issue, actor, role, rationale, previous_tag, tag) VALUES(?,?,?,?,?,?,?,?)",
                (package_id, seq, issue, actor, role, rationale, previous_tag, tag),
            )
            self._db.execute("UPDATE issues SET open=0 WHERE package_id=? AND issue=?", (package_id, issue))
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        if operation == "close_package":
            package_id = str(payload["package_id"])
            package = self._db.execute("SELECT required_types, closed FROM packages WHERE package_id=?", (package_id,)).fetchone()
            if package is None:
                raise KeyError("unknown_package")
            if package["closed"]:
                return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
            required = set(json.loads(package["required_types"]))
            present = {row["evidence_type"] for row in self._db.execute("SELECT evidence_type FROM evidence WHERE package_id=?", (package_id,))}
            missing = sorted(required - present)
            open_issues = self._db.execute("SELECT COUNT(*) AS n FROM issues WHERE package_id=? AND open=1", (package_id,)).fetchone()["n"]
            if missing:
                raise ValueError("missing_required_evidence:" + ",".join(missing))
            if open_issues:
                raise ValueError("unresolved_issues")
            self._db.execute("UPDATE packages SET closed=1 WHERE package_id=?", (package_id,))
            return {"ok": True, "schema": SCHEMA_VERSION, "snapshot": self._snapshot(package_id)}
        raise ValueError("unknown_operation")


class AuthorityServer:
    def __init__(self, socket_path: str, db_path: str, authorization_key_file: str, *, allowed_client_uid: int, socket_mode: int = 0o600, socket_gid: int | None = None):
        self._socket_path = socket_path
        self._socket_mode = socket_mode
        self._socket_gid = socket_gid
        self._store = AuthorityStore(db_path, _read_once_secret(authorization_key_file), allowed_client_uid)

    def serve_forever(self) -> None:
        path = Path(self._socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self._socket_path)
        if self._socket_gid is not None:
            os.chown(self._socket_path, -1, self._socket_gid)
        os.chmod(self._socket_path, self._socket_mode)
        server.listen(16)
        try:
            while True:
                connection, _ = server.accept()
                with connection:
                    peer_uid = -1
                    if hasattr(socket, "SO_PEERCRED"):
                        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
                        _pid, peer_uid, _gid = struct.unpack("3i", raw)
                    request_bytes = b""
                    while not request_bytes.endswith(b"\n"):
                        chunk = connection.recv(65536)
                        if not chunk:
                            break
                        request_bytes += chunk
                        if len(request_bytes) > 2_000_000:
                            break
                    try:
                        response = self._store.handle(json.loads(request_bytes.decode("utf-8")), peer_uid)
                    except Exception as exc:
                        response = {"ok": False, "error": "invalid_request", "detail": type(exc).__name__, "schema": SCHEMA_VERSION}
                    connection.sendall(json.dumps(response, sort_keys=True).encode("utf-8") + b"\n")
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
    parser.add_argument("--allowed-client-uid", type=int, default=os.getuid())
    parser.add_argument("--socket-mode", type=lambda value: int(value, 8), default=0o600)
    parser.add_argument("--socket-gid", type=int)
    args = parser.parse_args()
    AuthorityServer(
        args.socket,
        args.db,
        args.authorization_key_file,
        allowed_client_uid=args.allowed_client_uid,
        socket_mode=args.socket_mode,
        socket_gid=args.socket_gid,
    ).serve_forever()


if __name__ == "__main__":
    main()
