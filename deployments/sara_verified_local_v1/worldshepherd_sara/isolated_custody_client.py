from __future__ import annotations

import copy
import hashlib
import json
import socket
import struct
import uuid
from typing import Any

from .isolated_custody_service import SCHEMA_VERSION


class AuthorityUnavailable(RuntimeError):
    pass


class CustodyClient:
    """Thin client. Holds no authoritative custody or signing material."""

    def __init__(
        self,
        socket_path: str,
        *,
        expected_authority_uid: int,
        timeout_seconds: float = 2.0,
    ):
        self._socket_path = socket_path
        self._expected_authority_uid = int(expected_authority_uid)
        self._timeout_seconds = timeout_seconds

    def _verify_authority_peer(self, client: socket.socket) -> None:
        if not hasattr(socket, "SO_PEERCRED"):
            raise AuthorityUnavailable("authority peer authentication unavailable")
        try:
            raw = client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _pid, peer_uid, _gid = struct.unpack("3i", raw)
        except OSError as exc:
            raise AuthorityUnavailable("authority peer authentication failed") from exc
        if int(peer_uid) != self._expected_authority_uid:
            raise AuthorityUnavailable("authority peer identity mismatch")

    def _request(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        envelope = {
            "schema": SCHEMA_VERSION,
            "request_id": request_id or str(uuid.uuid4()),
            "operation": operation,
            "payload": copy.deepcopy(payload),
        }
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(self._timeout_seconds)
        try:
            client.connect(self._socket_path)
            self._verify_authority_peer(client)
            client.sendall(json.dumps(envelope, sort_keys=True).encode("utf-8") + b"\n")
            response_bytes = b""
            while not response_bytes.endswith(b"\n"):
                chunk = client.recv(65536)
                if not chunk:
                    break
                response_bytes += chunk
                if len(response_bytes) > 2_000_000:
                    raise AuthorityUnavailable("authority response exceeded client limit")
        except AuthorityUnavailable:
            raise
        except (OSError, TimeoutError) as exc:
            raise AuthorityUnavailable("isolated custody authority unavailable") from exc
        finally:
            client.close()
        try:
            response = json.loads(response_bytes.decode("utf-8"))
        except Exception as exc:
            raise AuthorityUnavailable("invalid authority response") from exc
        if response.get("schema") != SCHEMA_VERSION:
            raise AuthorityUnavailable("authority schema mismatch")
        return copy.deepcopy(response)

    def health(self) -> dict[str, Any]:
        return self._request("health", {})

    def get_audit(self, *, limit: int = 100) -> dict[str, Any]:
        return self._request("get_audit", {"limit": int(limit)})

    def register_package(
        self,
        *,
        package_id: str,
        authority_required: str,
        required_evidence_types: list[str] | tuple[str, ...],
        baseline_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "register_package",
            {
                "package_id": package_id,
                "authority_required": authority_required,
                "required_evidence_types": list(required_evidence_types),
                "baseline_id": baseline_id,
            },
            request_id=request_id,
        )

    def get_snapshot(self, package_id: str) -> dict[str, Any]:
        return self._request("get_snapshot", {"package_id": package_id})

    def ingest_evidence(
        self,
        *,
        package_id: str,
        evidence_id: str,
        evidence_type: str,
        version: int,
        baseline_id: str,
        record: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        detached = copy.deepcopy(record)
        digest = hashlib.sha256(
            json.dumps(detached, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return self._request(
            "ingest_evidence",
            {
                "package_id": package_id,
                "evidence_id": evidence_id,
                "evidence_type": evidence_type,
                "version": version,
                "baseline_id": baseline_id,
                "record": detached,
                "digest": digest,
            },
            request_id=request_id,
        )

    def open_issue(self, *, package_id: str, issue: str) -> dict[str, Any]:
        return self._request("open_issue", {"package_id": package_id, "issue": issue})

    def resolve_issue(
        self,
        *,
        package_id: str,
        issue: str,
        actor: str,
        role: str,
        rationale: str,
        authorization: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "resolve_issue",
            {
                "package_id": package_id,
                "issue": issue,
                "actor": actor,
                "role": role,
                "rationale": rationale,
                "authorization": copy.deepcopy(authorization),
            },
            request_id=request_id,
        )

    def close_package(self, package_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        return self._request("close_package", {"package_id": package_id}, request_id=request_id)
