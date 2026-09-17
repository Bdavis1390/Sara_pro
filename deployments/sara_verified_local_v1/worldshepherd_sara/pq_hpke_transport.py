from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM768PublicKey,
)
from cryptography.hazmat.primitives.hpke import AEAD, KDF, KEM, Suite
from pydantic import BaseModel, ConfigDict, Field, model_validator


PQ_HPKE_REQUEST_SCHEMA = "WS-PQ-HPKE-REQUEST-V1"
PQ_HPKE_RESPONSE_SCHEMA = "WS-PQ-HPKE-RESPONSE-V1"
PQ_HPKE_INNER_REQUEST_SCHEMA = "WS-PQ-HPKE-INNER-REQUEST-V1"
PQ_HPKE_INNER_RESPONSE_SCHEMA = "WS-PQ-HPKE-INNER-RESPONSE-V1"
PQ_HPKE_PUBLIC_KEY_SCHEMA = "WS-PQ-HPKE-PUBLIC-KEY-V1"
PQ_HPKE_KEM = "ML-KEM-768"
PQ_HPKE_KDF = "HKDF-SHA512"
PQ_HPKE_AEAD = "AES-256-GCM"
MAX_REQUEST_LIFETIME = timedelta(seconds=60)
MAX_FUTURE_SKEW = timedelta(seconds=15)
MAX_CIPHERTEXT_BYTES = 2 * 1024 * 1024
MAX_INNER_JSON_BYTES = 1024 * 1024
MAX_KEY_FILE_BYTES = 64 * 1024
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

SUITE = Suite(KEM.MLKEM768, KDF.HKDF_SHA512, AEAD.AES_256_GCM)


class PQHPKEError(ValueError):
    pass


class PQHPKEConfigError(PQHPKEError):
    pass


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64url(value: str, *, label: str, max_bytes: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise PQHPKEError(f"{label} must be non-empty base64url text")
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise PQHPKEError(f"{label} is invalid base64url") from exc
    if not raw or len(raw) > max_bytes:
        raise PQHPKEError(f"{label} size is invalid")
    return raw


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise PQHPKEError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_INNER_JSON_BYTES:
        raise PQHPKEError("PQ transport inner JSON exceeds limit")
    return raw


def _info(direction: str, service: str, operation: str, request_id: str) -> bytes:
    for value, label in ((service, "service"), (operation, "operation")):
        if not isinstance(value, str) or not value or len(value) > 128 or "|" in value:
            raise PQHPKEError(f"invalid PQ transport {label}")
    if not _REQUEST_ID.fullmatch(request_id):
        raise PQHPKEError("invalid PQ transport request_id")
    return f"WS-PQ-HPKE-V1|{direction}|{service}|{operation}|{request_id}".encode("ascii")


class PQPublicKeyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = PQ_HPKE_PUBLIC_KEY_SCHEMA
    key_id: str = Field(min_length=1, max_length=128)
    kem: str = PQ_HPKE_KEM
    kdf: str = PQ_HPKE_KDF
    aead: str = PQ_HPKE_AEAD
    public_key_b64url: str = Field(min_length=1, max_length=4096)
    fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PQRequestEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = PQ_HPKE_REQUEST_SCHEMA
    service: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    ciphertext_b64url: str = Field(min_length=1, max_length=3_000_000)
    reply_public_key_b64url: str = Field(min_length=1, max_length=4096)


class PQResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = PQ_HPKE_RESPONSE_SCHEMA
    service: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    ciphertext_b64url: str = Field(min_length=1, max_length=3_000_000)


class PQInnerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = PQ_HPKE_INNER_REQUEST_SCHEMA
    service: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    issued_at: datetime
    expires_at: datetime
    bearer_token: str = Field(min_length=32, max_length=1024)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_window(self) -> "PQInnerRequest":
        issued = _utc(self.issued_at)
        expires = _utc(self.expires_at)
        if expires <= issued:
            raise ValueError("PQ request expires_at must be after issued_at")
        if expires - issued > MAX_REQUEST_LIFETIME:
            raise ValueError("PQ request lifetime exceeds 60 seconds")
        return self


class PQInnerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = PQ_HPKE_INNER_RESPONSE_SCHEMA
    service: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    status_code: int = Field(ge=100, le=599)
    payload: dict[str, Any]


@dataclass(frozen=True)
class OpenedPQRequest:
    request: PQInnerRequest
    reply_public_key: MLKEM768PublicKey


@dataclass(frozen=True)
class PreparedPQRequest:
    envelope: PQRequestEnvelope
    reply_private_key: MLKEM768PrivateKey


def generate_private_key_pem() -> bytes:
    key = MLKEM768PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def load_private_key_pem(data: bytes) -> MLKEM768PrivateKey:
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise PQHPKEConfigError("PQ transport key must be unencrypted PEM") from exc
    if not isinstance(key, MLKEM768PrivateKey):
        raise PQHPKEConfigError("PQ transport key must contain ML-KEM-768 material")
    return key


def load_owned_private_key_file(path_value: str) -> MLKEM768PrivateKey:
    if not path_value:
        raise PQHPKEConfigError("PQ transport private-key file is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise PQHPKEConfigError("PQ transport private-key path must be absolute")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise PQHPKEConfigError("unable to inspect PQ transport private key") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise PQHPKEConfigError("PQ transport private key must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PQHPKEConfigError("unable to open PQ transport private key securely") from exc
    try:
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise PQHPKEConfigError("PQ transport private key must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise PQHPKEConfigError("PQ transport private key changed during secure open")
        if status.st_uid != os.geteuid():
            raise PQHPKEConfigError("PQ transport private key must be owned by service UID")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise PQHPKEConfigError("PQ transport private key must not grant group/other permissions")
        if status.st_size < 1 or status.st_size > MAX_KEY_FILE_BYTES:
            raise PQHPKEConfigError("PQ transport private-key size is invalid")
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            data = handle.read(MAX_KEY_FILE_BYTES + 1)
    finally:
        if fd >= 0:
            os.close(fd)
    if len(data) > MAX_KEY_FILE_BYTES:
        raise PQHPKEConfigError("PQ transport private key is too large")
    return load_private_key_pem(data)


def public_key_record(private_key: MLKEM768PrivateKey, *, key_id: str) -> PQPublicKeyRecord:
    if not _KEY_ID.fullmatch(key_id):
        raise PQHPKEConfigError("invalid PQ transport key_id")
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    if len(raw) != 1184:
        raise PQHPKEConfigError("ML-KEM-768 public key size mismatch")
    return PQPublicKeyRecord(
        key_id=key_id,
        public_key_b64url=_b64url(raw),
        fingerprint_sha256=hashlib.sha256(raw).hexdigest(),
    )


def public_key_from_record(record: PQPublicKeyRecord, *, expected_fingerprint: str | None = None) -> MLKEM768PublicKey:
    if record.kem != PQ_HPKE_KEM or record.kdf != PQ_HPKE_KDF or record.aead != PQ_HPKE_AEAD:
        raise PQHPKEError("unsupported PQ transport suite")
    raw = _unb64url(record.public_key_b64url, label="PQ transport public key", max_bytes=1184)
    if len(raw) != 1184:
        raise PQHPKEError("ML-KEM-768 public key must be 1184 bytes")
    fingerprint = hashlib.sha256(raw).hexdigest()
    if fingerprint != record.fingerprint_sha256:
        raise PQHPKEError("PQ transport public-key fingerprint mismatch")
    if expected_fingerprint is not None and fingerprint != expected_fingerprint:
        raise PQHPKEError("PQ transport public key is not pinned")
    try:
        return MLKEM768PublicKey.from_public_bytes(raw)
    except ValueError as exc:
        raise PQHPKEError("invalid ML-KEM-768 public key") from exc


def prepare_request(
    *,
    service: str,
    operation: str,
    request_id: str,
    bearer_token: str,
    payload: dict[str, Any],
    recipient_public_key: MLKEM768PublicKey,
    now: datetime | None = None,
    lifetime_seconds: int = 30,
) -> PreparedPQRequest:
    if not 1 <= lifetime_seconds <= int(MAX_REQUEST_LIFETIME.total_seconds()):
        raise PQHPKEError("invalid PQ request lifetime")
    current = _utc(now or datetime.now(timezone.utc))
    reply_private = MLKEM768PrivateKey.generate()
    reply_raw = reply_private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    inner = PQInnerRequest(
        service=service,
        operation=operation,
        request_id=request_id,
        issued_at=current,
        expires_at=current + timedelta(seconds=lifetime_seconds),
        bearer_token=bearer_token,
        payload=payload,
    )
    ciphertext = SUITE.encrypt(
        _canonical(inner.model_dump(mode="json")),
        recipient_public_key,
        info=_info("request", service, operation, request_id),
    )
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise PQHPKEError("PQ request ciphertext exceeds limit")
    return PreparedPQRequest(
        envelope=PQRequestEnvelope(
            service=service,
            operation=operation,
            request_id=request_id,
            ciphertext_b64url=_b64url(ciphertext),
            reply_public_key_b64url=_b64url(reply_raw),
        ),
        reply_private_key=reply_private,
    )


def open_request(
    envelope: PQRequestEnvelope,
    *,
    recipient_private_key: MLKEM768PrivateKey,
    now: datetime | None = None,
) -> OpenedPQRequest:
    ciphertext = _unb64url(
        envelope.ciphertext_b64url,
        label="PQ request ciphertext",
        max_bytes=MAX_CIPHERTEXT_BYTES,
    )
    try:
        plaintext = SUITE.decrypt(
            ciphertext,
            recipient_private_key,
            info=_info("request", envelope.service, envelope.operation, envelope.request_id),
        )
    except (InvalidTag, ValueError) as exc:
        raise PQHPKEError("PQ request decryption failed") from exc
    try:
        inner = PQInnerRequest.model_validate_json(plaintext)
    except ValueError as exc:
        raise PQHPKEError("PQ request plaintext is invalid") from exc
    if (
        inner.service != envelope.service
        or inner.operation != envelope.operation
        or inner.request_id != envelope.request_id
    ):
        raise PQHPKEError("PQ request outer/inner binding mismatch")
    current = _utc(now or datetime.now(timezone.utc))
    issued = _utc(inner.issued_at)
    expires = _utc(inner.expires_at)
    if issued > current + MAX_FUTURE_SKEW:
        raise PQHPKEError("PQ request issued too far in future")
    if current >= expires:
        raise PQHPKEError("PQ request expired")
    reply_raw = _unb64url(
        envelope.reply_public_key_b64url,
        label="PQ reply public key",
        max_bytes=1184,
    )
    if len(reply_raw) != 1184:
        raise PQHPKEError("PQ reply public key must be 1184 bytes")
    try:
        reply_public = MLKEM768PublicKey.from_public_bytes(reply_raw)
    except ValueError as exc:
        raise PQHPKEError("invalid PQ reply public key") from exc
    return OpenedPQRequest(request=inner, reply_public_key=reply_public)


def prepare_response(
    *,
    service: str,
    operation: str,
    request_id: str,
    status_code: int,
    payload: dict[str, Any],
    reply_public_key: MLKEM768PublicKey,
) -> PQResponseEnvelope:
    inner = PQInnerResponse(
        service=service,
        operation=operation,
        request_id=request_id,
        status_code=status_code,
        payload=payload,
    )
    ciphertext = SUITE.encrypt(
        _canonical(inner.model_dump(mode="json")),
        reply_public_key,
        info=_info("response", service, operation, request_id),
    )
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise PQHPKEError("PQ response ciphertext exceeds limit")
    return PQResponseEnvelope(
        service=service,
        operation=operation,
        request_id=request_id,
        ciphertext_b64url=_b64url(ciphertext),
    )


def open_response(
    envelope: PQResponseEnvelope,
    *,
    reply_private_key: MLKEM768PrivateKey,
) -> PQInnerResponse:
    ciphertext = _unb64url(
        envelope.ciphertext_b64url,
        label="PQ response ciphertext",
        max_bytes=MAX_CIPHERTEXT_BYTES,
    )
    try:
        plaintext = SUITE.decrypt(
            ciphertext,
            reply_private_key,
            info=_info("response", envelope.service, envelope.operation, envelope.request_id),
        )
    except (InvalidTag, ValueError) as exc:
        raise PQHPKEError("PQ response decryption failed") from exc
    try:
        inner = PQInnerResponse.model_validate_json(plaintext)
    except ValueError as exc:
        raise PQHPKEError("PQ response plaintext is invalid") from exc
    if (
        inner.service != envelope.service
        or inner.operation != envelope.operation
        or inner.request_id != envelope.request_id
    ):
        raise PQHPKEError("PQ response outer/inner binding mismatch")
    return inner
