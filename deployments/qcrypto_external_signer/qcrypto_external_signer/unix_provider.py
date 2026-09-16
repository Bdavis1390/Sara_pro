"""Unix-domain RPC boundary for the opaque signer provider.

This module makes the external signer a separate process boundary for CI/reference
use. The custody process receives only public descriptor data and provider results;
the reference ML-DSA private key is created and retained inside the signer process.

Security boundary:
- Unix-domain sockets only; there is no TCP listener.
- Socket directory must not be group/world accessible.
- Socket itself is owner read/write only (0600).
- No RPC exists for exporting private/secret key material.
- The RPC surface is describe, begin_sign, and reconcile only.
- This is a software reference boundary, not a production HSM/KMS or FIPS module.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import socketserver
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .opaque_provider import (
    OpaqueSignerProvider,
    ProviderAmbiguousOutcome,
    ProviderConflict,
    ProviderError,
    ProviderResult,
    ProviderState,
    ReferenceOpaqueMlDsa65Provider,
)

_MAX_FRAME_BYTES = 262_144
_PROTOCOL = "WS-QCRYPTO-OPAQUE-PROVIDER-UDS-V1"


class ProviderRpcError(ProviderError):
    pass


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: Any, *, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ProviderRpcError(f"{label} must be a non-empty base64url string")
    raw = value.encode("ascii")
    try:
        decoded = base64.b64decode(
            raw + b"=" * (-len(raw) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise ProviderRpcError(f"{label} is invalid base64url") from exc
    if len(decoded) > _MAX_FRAME_BYTES:
        raise ProviderRpcError(f"{label} exceeds the RPC size limit")
    return decoded


def _result_from_dict(value: Any) -> ProviderResult:
    if not isinstance(value, dict):
        raise ProviderRpcError("provider result must be an object")
    try:
        state = ProviderState(value["state"])
        result = ProviderResult(
            operation_id=str(value["operation_id"]),
            state=state,
            key_handle=str(value["key_handle"]),
            algorithm=str(value["algorithm"]),
            message_sha256=str(value["message_sha256"]),
            context_sha256=str(value["context_sha256"]),
            signature_b64url=(
                None if value.get("signature_b64url") is None else str(value["signature_b64url"])
            ),
            safe_to_retry=value.get("safe_to_retry") is True,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ProviderRpcError("provider result is malformed") from exc
    return result


def _secure_socket_path(path: Path) -> None:
    if not path.is_absolute():
        raise ProviderRpcError("opaque signer socket path must be absolute")
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    pst = parent.stat()
    if pst.st_uid != os.getuid():
        raise ProviderRpcError("opaque signer socket directory must be owned by the signer user")
    if stat.S_IMODE(pst.st_mode) & 0o077:
        raise ProviderRpcError("opaque signer socket directory must not be group/world accessible")
    if path.exists() or path.is_symlink():
        raise ProviderRpcError("opaque signer socket path already exists")


def _verify_client_socket(path: Path) -> None:
    st = path.stat()
    if not stat.S_ISSOCK(st.st_mode):
        raise ProviderRpcError("opaque signer endpoint is not a Unix socket")
    if st.st_uid != os.getuid():
        raise ProviderRpcError("opaque signer socket is not owned by the current custody user")
    if stat.S_IMODE(st.st_mode) & 0o177:
        raise ProviderRpcError("opaque signer socket permissions are too broad")
    pst = path.parent.stat()
    if stat.S_IMODE(pst.st_mode) & 0o077:
        raise ProviderRpcError("opaque signer socket directory permissions are too broad")


class _ProviderRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(_MAX_FRAME_BYTES + 2)
        if not raw or len(raw) > _MAX_FRAME_BYTES or not raw.endswith(b"\n"):
            self._reply({"ok": False, "error": "INVALID_FRAME"})
            return
        try:
            request = json.loads(raw)
            if not isinstance(request, dict) or request.get("protocol") != _PROTOCOL:
                raise ProviderRpcError("unsupported provider RPC protocol")
            command = request.get("command")
            provider = self.server.provider  # type: ignore[attr-defined]
            if command == "describe":
                self._reply(
                    {
                        "ok": True,
                        "protocol": _PROTOCOL,
                        "descriptor": {
                            "algorithm": provider.algorithm,
                            "key_handle": provider.key_handle,
                            "public_key_b64url": _b64(provider.public_key_bytes),
                            "fingerprint_sha256": provider.fingerprint_sha256,
                            "signer_process_id": os.getpid(),
                            "private_key_export_supported": False,
                            "tcp_transport_supported": False,
                        },
                    }
                )
                return
            if command == "begin_sign":
                operation_id = request.get("operation_id")
                if not isinstance(operation_id, str) or not operation_id:
                    raise ProviderRpcError("operation_id is required")
                message = _unb64(request.get("message_b64url"), label="message")
                context = _unb64(request.get("context_b64url"), label="context")
                try:
                    result = provider.begin_sign(operation_id, message, context)
                except ProviderAmbiguousOutcome as exc:
                    self._reply(
                        {
                            "ok": False,
                            "error": "AMBIGUOUS_OUTCOME",
                            "operation_id": exc.operation_id,
                        }
                    )
                    return
                self._reply({"ok": True, "protocol": _PROTOCOL, "result": result.to_dict()})
                return
            if command == "reconcile":
                operation_id = request.get("operation_id")
                if not isinstance(operation_id, str) or not operation_id:
                    raise ProviderRpcError("operation_id is required")
                result = provider.reconcile(operation_id)
                self._reply({"ok": True, "protocol": _PROTOCOL, "result": result.to_dict()})
                return
            raise ProviderRpcError("unsupported provider RPC command")
        except ProviderConflict:
            self._reply({"ok": False, "error": "PROVIDER_CONFLICT"})
        except (ProviderError, ProviderRpcError, ValueError, TypeError, json.JSONDecodeError):
            self._reply({"ok": False, "error": "INVALID_REQUEST"})

    def _reply(self, value: dict[str, Any]) -> None:
        encoded = _canonical(value) + b"\n"
        if len(encoded) > _MAX_FRAME_BYTES:
            encoded = b'{"error":"RESPONSE_TOO_LARGE","ok":false}\n'
        self.wfile.write(encoded)


class OpaqueProviderUnixServer(socketserver.UnixStreamServer):
    """Single-threaded signer RPC server; signing operations are serialized."""

    allow_reuse_address = False

    def __init__(self, socket_path: str | Path, provider: OpaqueSignerProvider) -> None:
        self.socket_path = Path(socket_path)
        _secure_socket_path(self.socket_path)
        self.provider = provider
        try:
            super().__init__(str(self.socket_path), _ProviderRequestHandler)
            os.chmod(self.socket_path, 0o600)
        except Exception:
            if self.socket_path.exists() and stat.S_ISSOCK(self.socket_path.stat().st_mode):
                self.socket_path.unlink()
            raise

    def server_close(self) -> None:
        try:
            super().server_close()
        finally:
            if self.socket_path.exists() and stat.S_ISSOCK(self.socket_path.stat().st_mode):
                self.socket_path.unlink()


def serve_reference_provider(
    socket_path: str | Path,
    *,
    key_handle: str = "ref-hsm://qcrypto/ml-dsa-65/ci-key-1",
    ack_loss_once: bool = False,
) -> None:
    """Run the CI/reference signer process until externally terminated."""
    provider = ReferenceOpaqueMlDsa65Provider(
        key_handle=key_handle,
        ack_loss_once=ack_loss_once,
    )
    with OpaqueProviderUnixServer(socket_path, provider) as server:
        server.serve_forever(poll_interval=0.1)


@dataclass(frozen=True)
class ProviderDescriptor:
    algorithm: str
    key_handle: str
    public_key_bytes: bytes
    fingerprint_sha256: str
    signer_process_id: int


class UnixOpaqueSignerProviderClient:
    """OpaqueSignerProvider client backed only by a secured Unix-domain socket."""

    def __init__(self, socket_path: str | Path) -> None:
        self._socket_path = Path(socket_path)
        descriptor = self._describe()
        if descriptor.algorithm != "ML-DSA-65":
            raise ProviderRpcError("unsupported remote signer algorithm")
        if hashlib.sha256(descriptor.public_key_bytes).hexdigest() != descriptor.fingerprint_sha256:
            raise ProviderRpcError("remote signer public-key fingerprint is inconsistent")
        self._descriptor = descriptor

    def _rpc(self, request: dict[str, Any]) -> dict[str, Any]:
        _verify_client_socket(self._socket_path)
        payload = {"protocol": _PROTOCOL, **request}
        encoded = _canonical(payload) + b"\n"
        if len(encoded) > _MAX_FRAME_BYTES:
            raise ProviderRpcError("provider RPC request exceeds the size limit")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5.0)
            client.connect(str(self._socket_path))
            client.sendall(encoded)
            response = bytearray()
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                response.extend(chunk)
                if len(response) > _MAX_FRAME_BYTES:
                    raise ProviderRpcError("provider RPC response exceeds the size limit")
                if response.endswith(b"\n"):
                    break
        try:
            value = json.loads(bytes(response))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderRpcError("provider RPC returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ProviderRpcError("provider RPC returned an invalid object")
        if value.get("ok") is not True:
            error = value.get("error")
            if error == "AMBIGUOUS_OUTCOME":
                operation_id = value.get("operation_id")
                if not isinstance(operation_id, str):
                    raise ProviderRpcError("ambiguous provider response omitted operation ID")
                raise ProviderAmbiguousOutcome(operation_id, "remote signer outcome is ambiguous")
            if error == "PROVIDER_CONFLICT":
                raise ProviderConflict("remote signer reported an operation conflict")
            raise ProviderRpcError(f"remote signer rejected request: {error}")
        if value.get("protocol") != _PROTOCOL:
            raise ProviderRpcError("provider RPC response protocol mismatch")
        return value

    def _describe(self) -> ProviderDescriptor:
        value = self._rpc({"command": "describe"})
        raw = value.get("descriptor")
        if not isinstance(raw, dict):
            raise ProviderRpcError("provider descriptor is missing")
        if raw.get("private_key_export_supported") is not False:
            raise ProviderRpcError("remote signer does not assert private-key non-exportability")
        if raw.get("tcp_transport_supported") is not False:
            raise ProviderRpcError("remote signer unexpectedly advertises TCP transport")
        public_key = _unb64(raw.get("public_key_b64url"), label="provider public key")
        try:
            pid = int(raw["signer_process_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderRpcError("provider descriptor process ID is invalid") from exc
        return ProviderDescriptor(
            algorithm=str(raw.get("algorithm")),
            key_handle=str(raw.get("key_handle")),
            public_key_bytes=public_key,
            fingerprint_sha256=str(raw.get("fingerprint_sha256")),
            signer_process_id=pid,
        )

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    @property
    def algorithm(self) -> str:
        return self._descriptor.algorithm

    @property
    def key_handle(self) -> str:
        return self._descriptor.key_handle

    @property
    def public_key_bytes(self) -> bytes:
        return self._descriptor.public_key_bytes

    @property
    def fingerprint_sha256(self) -> str:
        return self._descriptor.fingerprint_sha256

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        value = self._rpc(
            {
                "command": "begin_sign",
                "operation_id": operation_id,
                "message_b64url": _b64(message),
                "context_b64url": _b64(context),
            }
        )
        return _result_from_dict(value.get("result"))

    def reconcile(self, operation_id: str) -> ProviderResult:
        value = self._rpc({"command": "reconcile", "operation_id": operation_id})
        return _result_from_dict(value.get("result"))
