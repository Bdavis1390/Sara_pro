from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .prime_configuration_custody import PrimeEnvironment
from .prime_sentinel_authorization import (
    MAX_ASSERTION_LIFETIME,
    PRIME_SENTINEL_AUTHZ_SCHEMA,
    PrimeSentinelAuthorizationAssertion,
    canonical_authorization_message,
)


KEY_FILE_ENV = "PRIME_SENTINEL_PRIVATE_KEY_FILE"
KEY_ID_ENV = "PRIME_SENTINEL_SIGNING_KEY_ID"
SERVICE_TOKEN_ENV = "PRIME_SENTINEL_SERVICE_TOKEN"
MAX_KEY_FILE_BYTES = 16 * 1024
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
    schema: str = "WS-PRIME-SENTINEL-PUBLIC-KEY-V1"
    issuer: str = "PRIME_SENTINEL"
    algorithm: str = "Ed25519"
    key_id: str
    public_key_b64url: str
    fingerprint_sha256: str


class PrimeSentinelIssueResponse(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-ISSUE-RESPONSE-V1"
    assertion: PrimeSentinelAuthorizationAssertion


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _load_private_key_file(path_value: str) -> Ed25519PrivateKey:
    if not path_value:
        raise PrimeSentinelServiceConfigError(f"{KEY_FILE_ENV} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise PrimeSentinelServiceConfigError(f"{KEY_FILE_ENV} must be an absolute path")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PrimeSentinelServiceConfigError(
            "unable to open PRIME SENTINEL private-key file securely"
        ) from exc

    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL private-key path must be a regular file"
            )
        if file_status.st_uid != os.geteuid():
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL private-key file must be owned by the service UID"
            )
        if stat.S_IMODE(file_status.st_mode) & 0o077:
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL private-key file must not grant group/other permissions"
            )
        if file_status.st_size < 1 or file_status.st_size > MAX_KEY_FILE_BYTES:
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL private-key file size is invalid"
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_KEY_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if len(data) > MAX_KEY_FILE_BYTES:
        raise PrimeSentinelServiceConfigError("PRIME SENTINEL private-key file is too large")
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise PrimeSentinelServiceConfigError(
            "PRIME SENTINEL private-key file must contain an unencrypted PEM private key"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise PrimeSentinelServiceConfigError(
            "PRIME SENTINEL private-key file must contain an Ed25519 private key"
        )
    return key


def _load_service_token() -> str:
    token = os.getenv(SERVICE_TOKEN_ENV, "")
    if len(token) < MIN_SERVICE_TOKEN_CHARS:
        raise PrimeSentinelServiceConfigError(
            f"{SERVICE_TOKEN_ENV} must be at least {MIN_SERVICE_TOKEN_CHARS} characters"
        )
    for other_name in ("SARA_ADMIN_TOKEN", "SARA_RELAY_TOKEN"):
        other = os.getenv(other_name, "")
        if other and hmac.compare_digest(token, other):
            raise PrimeSentinelServiceConfigError(
                f"{SERVICE_TOKEN_ENV} must be independent from {other_name}"
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


class PrimeSentinelSigner:
    def __init__(
        self,
        *,
        private_key: Ed25519PrivateKey,
        key_id: str,
        service_token: str,
    ) -> None:
        self._private_key = private_key
        self.key_id = key_id
        self.service_token = service_token
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()

    @classmethod
    def from_environment(cls) -> "PrimeSentinelSigner":
        return cls(
            private_key=_load_private_key_file(os.getenv(KEY_FILE_ENV, "")),
            key_id=_load_key_id(),
            service_token=_load_service_token(),
        )

    def public_key_record(self) -> PrimeSentinelPublicKey:
        return PrimeSentinelPublicKey(
            key_id=self.key_id,
            public_key_b64url=self.public_key_b64url,
            fingerprint_sha256=self.fingerprint_sha256,
        )

    def issue(
        self,
        request: PrimeSentinelIssueRequest,
        *,
        now: datetime | None = None,
    ) -> PrimeSentinelAuthorizationAssertion:
        lifetime = timedelta(seconds=request.lifetime_seconds)
        if lifetime > MAX_ASSERTION_LIFETIME:
            raise ValueError("authorization lifetime exceeds PRIME SENTINEL maximum")
        issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        unsigned = PrimeSentinelAuthorizationAssertion(
            schema=PRIME_SENTINEL_AUTHZ_SCHEMA,
            issuer="PRIME_SENTINEL",
            key_id=self.key_id,
            authorization_id=f"PSAUTH-{uuid4()}",
            prime_id=request.prime_id,
            action="REQUALIFICATION_RELEASE",
            target_environment=request.target_environment,
            issued_at=issued,
            expires_at=issued + lifetime,
            nonce=secrets.token_urlsafe(24),
            signature_b64url="UNSIGNED",
        )
        signature = self._private_key.sign(canonical_authorization_message(unsigned))
        return unsigned.model_copy(update={"signature_b64url": _b64url(signature)})


def create_prime_sentinel_app() -> FastAPI:
    signer = PrimeSentinelSigner.from_environment()
    app = FastAPI(
        title="Worldshepherd PRIME SENTINEL Authorization Service",
        version="1.4",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.signer = signer

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
        return {"ok": True, "service": "PRIME_SENTINEL", "version": "1.4"}

    @app.get("/readyz")
    def readyz() -> dict[str, object]:
        return {
            "ok": True,
            "service": "PRIME_SENTINEL",
            "signing_key_id": signer.key_id,
            "algorithm": "Ed25519",
        }

    @app.get("/v1/public-key", response_model=PrimeSentinelPublicKey)
    def public_key() -> PrimeSentinelPublicKey:
        return signer.public_key_record()

    @app.post("/v1/requalification-release", response_model=PrimeSentinelIssueResponse)
    def issue_requalification_release(
        body: PrimeSentinelIssueRequest,
        request: Request,
    ) -> PrimeSentinelIssueResponse:
        _require_bearer(request, signer.service_token)
        assertion = signer.issue(body)
        return PrimeSentinelIssueResponse(assertion=assertion)

    return app
