from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import sqlite3
import stat
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .prime_configuration_custody import PrimeEnvironment
from .prime_sentinel_authorization import (
    PRIME_SENTINEL_AUTHZ_SCHEMA,
    PRIME_SENTINEL_DEFAULT_ALGORITHM,
    PRIME_SENTINEL_LEGACY_ALGORITHM,
    PRIME_SENTINEL_MLDSA65_CONTEXT,
    PrimeSentinelAuthorizationAssertion,
    canonical_authorization_message,
)
from .prime_sentinel_issuance_store import (
    REQUEST_ID_HEADER,
    IssuanceRecord,
    PrimeSentinelIssuanceStore,
    PrimeSentinelIssuanceStoreError,
    PrimeSentinelLedgerFull,
    PrimeSentinelRequestConflict,
    parse_utc,
    validate_request_id,
)
from .prime_sentinel_ledger_integrity import verify_issuance_ledger_integrity


KEY_FILE_ENV = "PRIME_SENTINEL_PRIVATE_KEY_FILE"
KEY_ID_ENV = "PRIME_SENTINEL_SIGNING_KEY_ID"
SIGNING_ALGORITHM_ENV = "PRIME_SENTINEL_SIGNING_ALGORITHM"
SERVICE_TOKEN_FILE_ENV = "PRIME_SENTINEL_SERVICE_TOKEN_FILE"
MAX_KEY_FILE_BYTES = 64 * 1024
MAX_SERVICE_TOKEN_FILE_BYTES = 4 * 1024
MIN_SERVICE_TOKEN_CHARS = 32
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class PrimeSentinelServiceConfigError(RuntimeError):
    pass


class PrimeSentinelIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prime_id: str = Field(min_length=1, max_length=128)
    target_environment: PrimeEnvironment
    lifetime_seconds: int = Field(default=300, ge=1, le=900)


class PrimeSentinelPublicKey(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-PUBLIC-KEY-V2"
    issuer: str = "PRIME_SENTINEL"
    algorithm: str
    key_id: str
    public_key_b64url: str
    fingerprint_sha256: str
    signature_context: str | None = None


class PrimeSentinelIssueResponse(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-ISSUE-RESPONSE-V1"
    assertion: PrimeSentinelAuthorizationAssertion


class PrimeSentinelIssuanceStatus(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-ISSUANCE-STATUS-V2"
    request_id: str
    state: str
    authorization_id: str
    prime_id: str
    target_environment: PrimeEnvironment
    key_id: str
    key_fingerprint_sha256: str
    signing_algorithm: str
    post_quantum_signature_protection: bool
    issued_at: str
    expires_at: str
    prepared_at: str
    signed_at: str | None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _read_owned_secret_file(
    path_value: str,
    *,
    env_name: str,
    label: str,
    max_bytes: int,
) -> bytes:
    if not path_value:
        raise PrimeSentinelServiceConfigError(f"{env_name} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise PrimeSentinelServiceConfigError(f"{env_name} must be an absolute path")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise PrimeSentinelServiceConfigError(f"unable to inspect {label}") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise PrimeSentinelServiceConfigError(f"{label} must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PrimeSentinelServiceConfigError(f"unable to open {label} securely") from exc
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise PrimeSentinelServiceConfigError(f"{label} must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (file_status.st_dev, file_status.st_ino):
            raise PrimeSentinelServiceConfigError(f"{label} changed during secure open")
        if file_status.st_uid != os.geteuid():
            raise PrimeSentinelServiceConfigError(f"{label} must be owned by the service UID")
        if stat.S_IMODE(file_status.st_mode) & 0o077:
            raise PrimeSentinelServiceConfigError(
                f"{label} must not grant group/other permissions"
            )
        if file_status.st_size < 1 or file_status.st_size > max_bytes:
            raise PrimeSentinelServiceConfigError(f"{label} size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(max_bytes + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > max_bytes:
        raise PrimeSentinelServiceConfigError(f"{label} is too large")
    return data


def _load_signing_algorithm() -> str:
    algorithm = os.getenv(SIGNING_ALGORITHM_ENV, PRIME_SENTINEL_DEFAULT_ALGORITHM).strip()
    if algorithm == "ML-DSA":
        algorithm = PRIME_SENTINEL_DEFAULT_ALGORITHM
    if algorithm not in {PRIME_SENTINEL_DEFAULT_ALGORITHM, PRIME_SENTINEL_LEGACY_ALGORITHM}:
        raise PrimeSentinelServiceConfigError(
            f"unsupported PRIME SENTINEL signing algorithm: {algorithm}"
        )
    return algorithm


def _load_private_key_file(path_value: str, *, algorithm: str):
    data = _read_owned_secret_file(
        path_value,
        env_name=KEY_FILE_ENV,
        label="PRIME SENTINEL private-key file",
        max_bytes=MAX_KEY_FILE_BYTES,
    )
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise PrimeSentinelServiceConfigError(
            "PRIME SENTINEL private-key file must contain an unencrypted PEM private key"
        ) from exc
    if algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM:
        if not isinstance(key, MLDSA65PrivateKey):
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL ML-DSA-65 mode requires ML-DSA-65 private key material"
            )
        return key
    if algorithm == PRIME_SENTINEL_LEGACY_ALGORITHM:
        if not isinstance(key, Ed25519PrivateKey):
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL Ed25519 mode requires Ed25519 private key material"
            )
        return key
    raise PrimeSentinelServiceConfigError("unsupported PRIME SENTINEL private key algorithm")


def _load_service_token_file(path_value: str) -> str:
    data = _read_owned_secret_file(
        path_value,
        env_name=SERVICE_TOKEN_FILE_ENV,
        label="PRIME SENTINEL service-token file",
        max_bytes=MAX_SERVICE_TOKEN_FILE_BYTES,
    )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrimeSentinelServiceConfigError(
            "PRIME SENTINEL service-token file must be UTF-8 text"
        ) from exc
    token = text.rstrip("\r\n")
    if not token or token != token.strip() or "\n" in token or "\r" in token:
        raise PrimeSentinelServiceConfigError(
            "PRIME SENTINEL service-token file must contain one token"
        )
    if len(token) < MIN_SERVICE_TOKEN_CHARS:
        raise PrimeSentinelServiceConfigError(
            f"PRIME SENTINEL service token must be at least {MIN_SERVICE_TOKEN_CHARS} characters"
        )
    for other_name in ("SARA_ADMIN_TOKEN", "SARA_RELAY_TOKEN"):
        other = os.getenv(other_name, "")
        if other and hmac.compare_digest(token, other):
            raise PrimeSentinelServiceConfigError(
                f"PRIME SENTINEL service token must be independent from {other_name}"
            )
    return token


def _load_key_id() -> str:
    key_id = os.getenv(KEY_ID_ENV, "").strip()
    if not _KEY_ID_PATTERN.fullmatch(key_id):
        raise PrimeSentinelServiceConfigError(
            f"{KEY_ID_ENV} must be 1-128 safe identifier characters"
        )
    return key_id


def _require_bearer(request: Request, expected_token: str) -> None:
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied:
        raise HTTPException(status_code=401, detail="PRIME SENTINEL bearer token required")
    if not hmac.compare_digest(supplied, expected_token):
        raise HTTPException(status_code=403, detail="PRIME SENTINEL bearer token rejected")


def _require_request_id(request: Request) -> str:
    raw = request.headers.get(REQUEST_ID_HEADER)
    if raw is None:
        raise HTTPException(status_code=400, detail=f"{REQUEST_ID_HEADER} is required")
    try:
        return validate_request_id(raw)
    except PrimeSentinelIssuanceStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class PrimeSentinelSigner:
    def __init__(
        self,
        *,
        private_key: Ed25519PrivateKey | MLDSA65PrivateKey,
        algorithm: str,
        key_id: str,
        service_token: str,
    ) -> None:
        self._private_key = private_key
        self.algorithm = algorithm
        self.key_id = key_id
        self.service_token = service_token
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        expected = 1952 if algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM else 32
        if len(public_bytes) != expected:
            raise PrimeSentinelServiceConfigError(
                f"PRIME SENTINEL {algorithm} public-key size mismatch"
            )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()
        self.signature_context = (
            PRIME_SENTINEL_MLDSA65_CONTEXT
            if algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM
            else None
        )

    @classmethod
    def from_environment(cls) -> "PrimeSentinelSigner":
        algorithm = _load_signing_algorithm()
        return cls(
            private_key=_load_private_key_file(
                os.getenv(KEY_FILE_ENV, ""),
                algorithm=algorithm,
            ),
            algorithm=algorithm,
            key_id=_load_key_id(),
            service_token=_load_service_token_file(os.getenv(SERVICE_TOKEN_FILE_ENV, "")),
        )

    @property
    def post_quantum_signature_protection(self) -> bool:
        return self.algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM

    def public_key_record(self) -> PrimeSentinelPublicKey:
        return PrimeSentinelPublicKey(
            algorithm=self.algorithm,
            key_id=self.key_id,
            public_key_b64url=self.public_key_b64url,
            fingerprint_sha256=self.fingerprint_sha256,
            signature_context=(
                self.signature_context.decode("ascii")
                if self.signature_context is not None
                else None
            ),
        )

    def _assertion_from_record(
        self,
        record: IssuanceRecord,
        *,
        signature_b64url: str,
    ) -> PrimeSentinelAuthorizationAssertion:
        return PrimeSentinelAuthorizationAssertion(
            schema=PRIME_SENTINEL_AUTHZ_SCHEMA,
            issuer="PRIME_SENTINEL",
            key_id=record.key_id,
            authorization_id=record.authorization_id,
            prime_id=record.prime_id,
            action="REQUALIFICATION_RELEASE",
            target_environment=PrimeEnvironment(record.target_environment),
            issued_at=parse_utc(record.issued_at),
            expires_at=parse_utc(record.expires_at),
            nonce=record.nonce,
            signature_b64url=signature_b64url,
        )

    def _sign(self, message: bytes) -> bytes:
        if self.algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM:
            assert isinstance(self._private_key, MLDSA65PrivateKey)
            return self._private_key.sign(message, PRIME_SENTINEL_MLDSA65_CONTEXT)
        if self.algorithm == PRIME_SENTINEL_LEGACY_ALGORITHM:
            assert isinstance(self._private_key, Ed25519PrivateKey)
            return self._private_key.sign(message)
        raise PrimeSentinelServiceConfigError("unsupported active PRIME SENTINEL signer")

    def issue_durable(
        self,
        body: PrimeSentinelIssueRequest,
        *,
        request_id: str,
        store: PrimeSentinelIssuanceStore,
    ) -> PrimeSentinelAuthorizationAssertion:
        record = store.prepare_or_get(
            request_id=request_id,
            prime_id=body.prime_id,
            target_environment=body.target_environment,
            lifetime_seconds=body.lifetime_seconds,
            key_id=self.key_id,
        )
        if record.state == "SIGNED":
            stored = record.assertion_dict()
            if stored is None:
                raise PrimeSentinelIssuanceStoreError(
                    "SIGNED issuance record is missing its assertion"
                )
            return PrimeSentinelAuthorizationAssertion.model_validate(stored)

        unsigned = self._assertion_from_record(record, signature_b64url="UNSIGNED")
        signature = self._sign(canonical_authorization_message(unsigned))
        signed = unsigned.model_copy(update={"signature_b64url": _b64url(signature)})
        persisted = store.mark_signed(
            request_id=request_id,
            signature_b64url=signed.signature_b64url,
            assertion=signed.model_dump(mode="json"),
        )
        stored = persisted.assertion_dict()
        if stored is None:
            raise PrimeSentinelIssuanceStoreError(
                "durable SIGNED issuance record is missing its assertion"
            )
        return PrimeSentinelAuthorizationAssertion.model_validate(stored)


def _bind_signing_key_identity(
    store: PrimeSentinelIssuanceStore,
    signer: PrimeSentinelSigner,
) -> None:
    bindings = {
        f"signing_key_fingerprint:{signer.key_id}": signer.fingerprint_sha256,
        f"signing_key_algorithm:{signer.key_id}": signer.algorithm,
    }
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(store.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")
        for name, expected in bindings.items():
            row = connection.execute(
                "SELECT value FROM metadata WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO metadata(name, value) VALUES(?, ?)",
                    (name, expected),
                )
            elif row["value"] != expected:
                if name.startswith("signing_key_fingerprint:"):
                    raise PrimeSentinelServiceConfigError(
                        "PRIME SENTINEL signing key ID is already bound to different key material"
                    )
                raise PrimeSentinelServiceConfigError(
                    "PRIME SENTINEL signing key ID is already bound to a different algorithm"
                )
        connection.commit()
    except sqlite3.Error as exc:
        raise PrimeSentinelServiceConfigError(
            "unable to bind PRIME SENTINEL signing key identity to issuance ledger"
        ) from exc
    finally:
        if connection is not None:
            connection.close()


def _bound_key_metadata(
    store: PrimeSentinelIssuanceStore,
    key_id: str,
) -> tuple[str, str]:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(store.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        fingerprint = connection.execute(
            "SELECT value FROM metadata WHERE name = ?",
            (f"signing_key_fingerprint:{key_id}",),
        ).fetchone()
        algorithm = connection.execute(
            "SELECT value FROM metadata WHERE name = ?",
            (f"signing_key_algorithm:{key_id}",),
        ).fetchone()
    except sqlite3.Error as exc:
        raise PrimeSentinelIssuanceStoreError(
            "unable to read signing-key binding from issuance ledger"
        ) from exc
    finally:
        if connection is not None:
            connection.close()
    if fingerprint is None or algorithm is None:
        raise PrimeSentinelIssuanceStoreError(
            "issuance ledger is missing the signing-key identity binding"
        )
    return str(fingerprint["value"]), str(algorithm["value"])


def _combined_ledger_status(store: PrimeSentinelIssuanceStore) -> dict[str, object]:
    basic = store.health()
    deep = verify_issuance_ledger_integrity(store)
    combined: dict[str, object] = {
        **basic,
        "cross_table_integrity_ok": bool(deep.get("ok")),
        "integrity_model": deep.get("integrity_model"),
        "tail_event_hash": deep.get("tail_event_hash"),
    }
    if not deep.get("ok"):
        combined["integrity_reason"] = deep.get("reason", "UNKNOWN")
    combined["ok"] = bool(basic.get("ok")) and bool(deep.get("ok"))
    return combined


def _status_from_record(
    record: IssuanceRecord,
    store: PrimeSentinelIssuanceStore,
) -> PrimeSentinelIssuanceStatus:
    fingerprint, algorithm = _bound_key_metadata(store, record.key_id)
    return PrimeSentinelIssuanceStatus(
        request_id=record.request_id,
        state=record.state,
        authorization_id=record.authorization_id,
        prime_id=record.prime_id,
        target_environment=PrimeEnvironment(record.target_environment),
        key_id=record.key_id,
        key_fingerprint_sha256=fingerprint,
        signing_algorithm=algorithm,
        post_quantum_signature_protection=(algorithm == PRIME_SENTINEL_DEFAULT_ALGORITHM),
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        prepared_at=record.prepared_at,
        signed_at=record.signed_at,
    )


def create_prime_sentinel_app() -> FastAPI:
    signer = PrimeSentinelSigner.from_environment()
    try:
        store = PrimeSentinelIssuanceStore.from_environment()
    except (PrimeSentinelIssuanceStoreError, sqlite3.Error) as exc:
        raise PrimeSentinelServiceConfigError(str(exc)) from exc
    _bind_signing_key_identity(store, signer)

    app = FastAPI(
        title="Worldshepherd PRIME SENTINEL Authorization Service",
        version="2.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.signer = signer
    app.state.issuance_store = store

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response

    @app.get("/livez")
    def livez() -> dict[str, object]:
        return {"ok": True, "service": "PRIME_SENTINEL", "version": "2.0"}

    @app.get("/readyz")
    def readyz() -> dict[str, object]:
        try:
            ledger = _combined_ledger_status(store)
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="issuance ledger unavailable") from exc
        if not ledger["ok"]:
            raise HTTPException(status_code=503, detail="issuance ledger integrity check failed")
        return {
            "ok": True,
            "service": "PRIME_SENTINEL",
            "signing_key_id": signer.key_id,
            "algorithm": signer.algorithm,
            "signature_context": (
                signer.signature_context.decode("ascii")
                if signer.signature_context is not None
                else None
            ),
            "post_quantum_signature_protection": signer.post_quantum_signature_protection,
            "issuance_ledger": "HEALTHY",
        }

    @app.get("/v1/public-key", response_model=PrimeSentinelPublicKey)
    def public_key() -> PrimeSentinelPublicKey:
        return signer.public_key_record()

    @app.get("/v1/issuance/{request_id}", response_model=PrimeSentinelIssuanceStatus)
    def issuance_status(request_id: str, request: Request) -> PrimeSentinelIssuanceStatus:
        _require_bearer(request, signer.service_token)
        try:
            record = store.get(validate_request_id(request_id))
            if record is None:
                raise HTTPException(status_code=404, detail="issuance request not found")
            return _status_from_record(record, store)
        except HTTPException:
            raise
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="issuance ledger unavailable") from exc

    @app.get("/v1/ledger-status")
    def ledger_status(request: Request) -> dict[str, object]:
        _require_bearer(request, signer.service_token)
        try:
            status = _combined_ledger_status(store)
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="issuance ledger unavailable") from exc
        if not status["ok"]:
            raise HTTPException(status_code=503, detail="issuance ledger integrity check failed")
        return {
            "schema": "WS-PRIME-SENTINEL-LEDGER-STATUS-V2",
            **status,
            "signing_algorithm": signer.algorithm,
            "post_quantum_signature_protection": signer.post_quantum_signature_protection,
            "claim_boundary": (
                "ML-DSA-65 protects PRIME authorization signatures when active. This does not by "
                "itself establish PQ-secure transport, external key custody, FIPS 140 module validation, "
                "or end-to-end post-quantum security."
            ),
        }

    @app.post("/v1/requalification-release", response_model=PrimeSentinelIssueResponse)
    def issue_requalification_release(
        body: PrimeSentinelIssueRequest,
        request: Request,
    ) -> PrimeSentinelIssueResponse:
        _require_bearer(request, signer.service_token)
        request_id = _require_request_id(request)
        try:
            assertion = signer.issue_durable(
                body,
                request_id=request_id,
                store=store,
            )
        except PrimeSentinelRequestConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PrimeSentinelLedgerFull as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="issuance persistence failed") from exc
        return PrimeSentinelIssueResponse(assertion=assertion)

    return app
