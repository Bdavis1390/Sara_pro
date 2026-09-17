from __future__ import annotations

import base64
import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey


CHECKPOINT_ALGORITHM_ENV = "ECHO_CHECKPOINT_ALGORITHM"
CHECKPOINT_PRIVATE_KEY_FILE_ENV = "ECHO_CHECKPOINT_PRIVATE_KEY_FILE"
CHECKPOINT_KEY_ID_ENV = "ECHO_CHECKPOINT_KEY_ID"
CHECKPOINT_SIGNATURE_CONTEXT = b"WS-ECHO-CHECKPOINT-V2"
MAX_CHECKPOINT_KEY_FILE_BYTES = 64 * 1024
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

CURRENT_EXECUTABLE_ALGORITHM = "ML-DSA-65"
LEGACY_EXECUTABLE_ALGORITHM = "Ed25519"
RECOGNIZED_PQ_TARGETS = frozenset({"ML-DSA", "ML-DSA-65", "SLH-DSA"})


class EchoCheckpointSignerError(RuntimeError):
    pass


class EchoCheckpointSignerConfigError(EchoCheckpointSignerError):
    pass


class EchoCheckpointSignerUnavailable(EchoCheckpointSignerError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _read_private_key(path_value: str, *, algorithm: str):
    if not path_value:
        raise EchoCheckpointSignerConfigError(f"{CHECKPOINT_PRIVATE_KEY_FILE_ENV} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise EchoCheckpointSignerConfigError(
            f"{CHECKPOINT_PRIVATE_KEY_FILE_ENV} must be an absolute path"
        )
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise EchoCheckpointSignerConfigError("unable to inspect ECHO checkpoint private key") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise EchoCheckpointSignerConfigError("ECHO checkpoint private key must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EchoCheckpointSignerConfigError("unable to open ECHO checkpoint private key securely") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise EchoCheckpointSignerConfigError("ECHO checkpoint private key must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise EchoCheckpointSignerConfigError("ECHO checkpoint private key changed during secure open")
        if status.st_uid != os.geteuid():
            raise EchoCheckpointSignerConfigError("ECHO checkpoint private key must be owned by the service UID")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise EchoCheckpointSignerConfigError(
                "ECHO checkpoint private key must not grant group/other permissions"
            )
        if status.st_size < 1 or status.st_size > MAX_CHECKPOINT_KEY_FILE_BYTES:
            raise EchoCheckpointSignerConfigError("ECHO checkpoint private key size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_CHECKPOINT_KEY_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_CHECKPOINT_KEY_FILE_BYTES:
        raise EchoCheckpointSignerConfigError("ECHO checkpoint private key is too large")
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise EchoCheckpointSignerConfigError(
            "ECHO checkpoint private key must be an unencrypted PEM private key"
        ) from exc

    if algorithm == CURRENT_EXECUTABLE_ALGORITHM:
        if not isinstance(key, MLDSA65PrivateKey):
            raise EchoCheckpointSignerConfigError(
                "ECHO checkpoint private key must contain ML-DSA-65 material"
            )
        return key
    if algorithm == LEGACY_EXECUTABLE_ALGORITHM:
        if not isinstance(key, Ed25519PrivateKey):
            raise EchoCheckpointSignerConfigError(
                "ECHO checkpoint private key must contain Ed25519 material"
            )
        return key
    raise EchoCheckpointSignerConfigError(f"unsupported key algorithm: {algorithm}")


def _load_key_id() -> str:
    value = os.getenv(CHECKPOINT_KEY_ID_ENV, "").strip()
    if not _KEY_ID_PATTERN.fullmatch(value):
        raise EchoCheckpointSignerConfigError(
            f"{CHECKPOINT_KEY_ID_ENV} must be 1-128 safe identifier characters"
        )
    return value


class CheckpointSigner(Protocol):
    algorithm: str
    key_id: str
    public_key_b64url: str
    fingerprint_sha256: str

    def sign(self, payload: bytes) -> bytes: ...

    def public_key_record(self) -> dict[str, str]: ...


@dataclass(frozen=True)
class MLDSA65CheckpointSigner:
    private_key: MLDSA65PrivateKey
    key_id: str

    @property
    def algorithm(self) -> str:
        return CURRENT_EXECUTABLE_ALGORITHM

    @property
    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_b64url(self) -> str:
        return _b64url(self.public_key_bytes)

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self.public_key_bytes).hexdigest()

    def sign(self, payload: bytes) -> bytes:
        return self.private_key.sign(payload, CHECKPOINT_SIGNATURE_CONTEXT)

    def public_key_record(self) -> dict[str, str]:
        return {
            "schema": "WS-ECHO-CHECKPOINT-PUBLIC-KEY-V1",
            "issuer": "ECHO_SENTINEL_LINK",
            "purpose": "PROVENANCE_CHECKPOINT_SIGNING",
            "algorithm": self.algorithm,
            "signature_context": CHECKPOINT_SIGNATURE_CONTEXT.decode("ascii"),
            "key_id": self.key_id,
            "public_key_b64url": self.public_key_b64url,
            "fingerprint_sha256": self.fingerprint_sha256,
        }


@dataclass(frozen=True)
class Ed25519CheckpointSigner:
    private_key: Ed25519PrivateKey
    key_id: str

    @property
    def algorithm(self) -> str:
        return LEGACY_EXECUTABLE_ALGORITHM

    @property
    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_b64url(self) -> str:
        return _b64url(self.public_key_bytes)

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self.public_key_bytes).hexdigest()

    def sign(self, payload: bytes) -> bytes:
        return self.private_key.sign(payload)

    def public_key_record(self) -> dict[str, str]:
        return {
            "schema": "WS-ECHO-CHECKPOINT-PUBLIC-KEY-V1",
            "issuer": "ECHO_SENTINEL_LINK",
            "purpose": "PROVENANCE_CHECKPOINT_SIGNING",
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "public_key_b64url": self.public_key_b64url,
            "fingerprint_sha256": self.fingerprint_sha256,
        }


def signer_from_environment() -> CheckpointSigner:
    requested = os.getenv(CHECKPOINT_ALGORITHM_ENV, CURRENT_EXECUTABLE_ALGORITHM).strip()
    if not requested:
        requested = CURRENT_EXECUTABLE_ALGORITHM
    if requested == "ML-DSA":
        requested = CURRENT_EXECUTABLE_ALGORITHM

    key_id = _load_key_id()
    path = os.getenv(CHECKPOINT_PRIVATE_KEY_FILE_ENV, "")

    if requested == CURRENT_EXECUTABLE_ALGORITHM:
        return MLDSA65CheckpointSigner(
            private_key=_read_private_key(path, algorithm=CURRENT_EXECUTABLE_ALGORITHM),
            key_id=key_id,
        )
    if requested == LEGACY_EXECUTABLE_ALGORITHM:
        return Ed25519CheckpointSigner(
            private_key=_read_private_key(path, algorithm=LEGACY_EXECUTABLE_ALGORITHM),
            key_id=key_id,
        )
    if requested == "SLH-DSA":
        raise EchoCheckpointSignerUnavailable(
            "SLH-DSA is a recognized post-quantum checkpoint migration target, "
            "but no verified runtime signer adapter is installed; refusing fallback"
        )
    raise EchoCheckpointSignerConfigError(
        f"unsupported ECHO checkpoint signing algorithm: {requested}"
    )


def runtime_capabilities() -> dict[str, object]:
    return {
        "schema": "WS-ECHO-CHECKPOINT-SIGNER-CAPABILITY-V2",
        "current_executable_algorithm": CURRENT_EXECUTABLE_ALGORITHM,
        "legacy_executable_algorithm": LEGACY_EXECUTABLE_ALGORITHM,
        "recognized_pq_targets": sorted(RECOGNIZED_PQ_TARGETS),
        "pq_runtime_signer_installed": True,
        "default_runtime_is_post_quantum": True,
        "classical_fallback_on_pq_request": False,
        "signature_context": CHECKPOINT_SIGNATURE_CONTEXT.decode("ascii"),
        "claim_boundary": (
            "ML-DSA-65 checkpoint signing is implemented in software using the pinned cryptography "
            "runtime. This capability statement does not by itself establish production deployment, "
            "FIPS 140 module validation, external key custody, or end-to-end post-quantum security."
        ),
    }
