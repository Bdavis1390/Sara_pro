from __future__ import annotations

import copy
import json
import socket
import struct
import uuid
from typing import Any

from .isolated_custody_service_v2 import SCHEMA_VERSION


class AuthorityUnavailable(RuntimeError):
    pass


class CustodyClientV2:
    """Thin authenticated client for the v2 isolated authority."""

    def __init__(self, socket_path: str, *, expected_authority_uid: int, timeout_seconds: float = 2.0):
        self._socket_path = socket_path
        self._expected_authority_uid = int(expected_authority_uid)
        self._timeout_seconds = timeout_seconds

    def _verify_peer(self, sock: socket.socket) -> None:
        if not hasattr(socket, "SO_PEERCRED"):
            raise AuthorityUnavailable("authority peer authentication unavailable")
        try:
            raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _pid, peer_uid, _gid = struct.unpack("3i", raw)
        except OSError as exc:
            raise AuthorityUnavailable("authority peer authentication failed") from exc
        if int(peer_uid) != self._expected_authority_uid:
            raise AuthorityUnavailable("authority peer identity mismatch")

    def _request(self, operation: str, payload: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
        envelope = {
            "schema": SCHEMA_VERSION,
            "request_id": request_id or str(uuid.uuid4()),
            "operation": operation,
            "payload": copy.deepcopy(payload),
        }
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self._timeout_seconds)
        try:
            sock.connect(self._socket_path)
            self._verify_peer(sock)
            sock.sendall(json.dumps(envelope, sort_keys=True).encode("utf-8") + b"\n")
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                if len(data) > 2_000_000:
                    raise AuthorityUnavailable("authority response exceeded client limit")
        except AuthorityUnavailable:
            raise
        except (OSError, TimeoutError) as exc:
            raise AuthorityUnavailable("isolated custody authority unavailable") from exc
        finally:
            sock.close()
        try:
            response = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise AuthorityUnavailable("invalid authority response") from exc
        if response.get("schema") != SCHEMA_VERSION:
            raise AuthorityUnavailable("authority schema mismatch")
        return copy.deepcopy(response)

    def health(self) -> dict[str, Any]:
        return self._request("health", {})

    def get_snapshot(self, package_id: str) -> dict[str, Any]:
        return self._request("get_snapshot", {"package_id": package_id})

    def register_package(self, *, package_id: str, authority_required: str, required_evidence_types: list[str], baseline_id: str, authorization: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        return self._request("register_package", {
            "package_id": package_id,
            "authority_required": authority_required,
            "required_evidence_types": list(required_evidence_types),
            "baseline_id": baseline_id,
            "authorization": copy.deepcopy(authorization),
        }, request_id=request_id)

    def ingest_evidence(self, *, package_id: str, evidence_id: str, evidence_type: str, version: int, baseline_id: str, source_id: str, previous_digest: str, record: dict[str, Any], authorization: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        return self._request("ingest_evidence", {
            "package_id": package_id,
            "evidence_id": evidence_id,
            "evidence_type": evidence_type,
            "version": int(version),
            "baseline_id": baseline_id,
            "source_id": source_id,
            "previous_digest": previous_digest,
            "record": copy.deepcopy(record),
            "authorization": copy.deepcopy(authorization),
        }, request_id=request_id)

    def open_issue(self, *, package_id: str, issue: str) -> dict[str, Any]:
        return self._request("open_issue", {"package_id": package_id, "issue": issue})

    def close_package(self, package_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        return self._request("close_package", {"package_id": package_id}, request_id=request_id)
