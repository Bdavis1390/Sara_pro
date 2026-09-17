from __future__ import annotations

import base64
import hashlib
import sqlite3
from typing import Any

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from .prime_sentinel_poo_authorization import _utc_iso
from .prime_sentinel_poo_issuance_store import (
    PoOIssuanceRecord,
    PrimeSentinelPoOIssuanceStore,
    PrimeSentinelPoOIssuanceStoreError,
    PrimeSentinelPoOLedgerFull,
    PrimeSentinelPoORequestConflict,
    parse_utc,
)
from .prime_sentinel_poo_service import (
    PrimeSentinelPoOIssueRequest,
    _bind_poo_signing_key_identity,
)
from .prime_sentinel_pq_poo_authorization import (
    PRIME_SENTINEL_PQ_ALGORITHM,
    PRIME_SENTINEL_PQ_CONTEXT,
    PRIME_SENTINEL_PQ_POO_AUTHZ_SCHEMA,
    PRIME_SENTINEL_PQ_STANDARD,
    PrimeSentinelPqPoOAuthorizationAssertion,
    canonical_pq_poo_authorization_message,
)
from .prime_sentinel_service import (
    KEY_FILE_ENV,
    MAX_KEY_FILE_BYTES,
    PrimeSentinelServiceConfigError,
    _load_key_id,
    _load_service_token_file,
    _read_owned_secret_file,
    _require_bearer,
    _require_request_id,
)


class PrimeSentinelPqPublicKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: str = "WS-PRIME-SENTINEL-PQ-PUBLIC-KEY-V1"
    issuer: str = "PRIME_SENTINEL_PQ"
    algorithm: str = PRIME_SENTINEL_PQ_ALGORITHM
    standard: str = PRIME_SENTINEL_PQ_STANDARD
    key_id: str
    public_key_b64url: str
    fingerprint_sha256: str


class PrimeSentinelPqPoOIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: str = "WS-PRIME-SENTINEL-PQ-POO-ISSUE-RESPONSE-V1"
    assertion: PrimeSentinelPqPoOAuthorizationAssertion


class PrimeSentinelPqSigner:
    def __init__(self, *, private_key: MLDSA65PrivateKey, key_id: str, service_token: str) -> None:
        self._private_key = private_key
        self.key_id = key_id
        self.service_token = service_token
        public_bytes = private_key.public_key().public_bytes_raw()
        self.public_key_b64url = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()

    @classmethod
    def from_environment(cls) -> "PrimeSentinelPqSigner":
        seed = _read_owned_secret_file(
            __import__("os").getenv(KEY_FILE_ENV, ""),
            env_name=KEY_FILE_ENV,
            label="PRIME SENTINEL PQ ML-DSA-65 seed file",
            max_bytes=MAX_KEY_FILE_BYTES,
        )
        if len(seed) != 32:
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL PQ ML-DSA-65 seed file must contain exactly 32 raw bytes"
            )
        try:
            key = MLDSA65PrivateKey.from_seed_bytes(seed)
        except (ValueError, UnsupportedAlgorithm) as exc:
            raise PrimeSentinelServiceConfigError(
                "ML-DSA-65 is unavailable or the private seed is invalid"
            ) from exc
        return cls(
            private_key=key,
            key_id=_load_key_id(),
            service_token=_load_service_token_file(
                __import__("os").getenv("PRIME_SENTINEL_SERVICE_TOKEN_FILE", "")
            ),
        )

    def public_key_record(self) -> PrimeSentinelPqPublicKey:
        return PrimeSentinelPqPublicKey(
            key_id=self.key_id,
            public_key_b64url=self.public_key_b64url,
            fingerprint_sha256=self.fingerprint_sha256,
        )


def _assertion_from_record(
    record: PoOIssuanceRecord,
    *,
    signature_b64url: str,
) -> PrimeSentinelPqPoOAuthorizationAssertion:
    return PrimeSentinelPqPoOAuthorizationAssertion(
        schema=PRIME_SENTINEL_PQ_POO_AUTHZ_SCHEMA,
        issuer="PRIME_SENTINEL_PQ",
        algorithm=PRIME_SENTINEL_PQ_ALGORITHM,
        standard=PRIME_SENTINEL_PQ_STANDARD,
        key_id=record.key_id,
        authorization_id=record.authorization_id,
        asset_id=record.asset_id,
        governance_projection_digest=record.governance_projection_digest,
        source_decision_digest=record.source_decision_digest,
        expected_registry_digest=record.expected_registry_digest,
        candidate_registry_digest=record.candidate_registry_digest,
        candidate_state_digest=record.candidate_state_digest,
        issued_at=parse_utc(record.issued_at),
        expires_at=parse_utc(record.expires_at),
        nonce=record.nonce,
        signature_b64url=signature_b64url,
    )


def _issue_pq_durable(
    signer: PrimeSentinelPqSigner,
    store: PrimeSentinelPoOIssuanceStore,
    body: PrimeSentinelPoOIssueRequest,
    *,
    request_id: str,
) -> PrimeSentinelPqPoOAuthorizationAssertion:
    record = store.prepare_or_get(
        request_id=request_id,
        asset_id=body.asset_id,
        governance_projection_digest=body.governance_projection_digest,
        source_decision_digest=body.source_decision_digest,
        expected_registry_digest=body.expected_registry_digest,
        candidate_registry_digest=body.candidate_registry_digest,
        candidate_state_digest=body.candidate_state_digest,
        lifetime_seconds=body.lifetime_seconds,
        key_id=signer.key_id,
    )
    if record.state == "SIGNED":
        stored = record.assertion_dict()
        if stored is None:
            raise PrimeSentinelPoOIssuanceStoreError(
                "SIGNED PQ PoO issuance record is missing its assertion"
            )
        return PrimeSentinelPqPoOAuthorizationAssertion.model_validate(stored)

    unsigned = _assertion_from_record(record, signature_b64url="UNSIGNED")
    try:
        signature = signer._private_key.sign(
            canonical_pq_poo_authorization_message(unsigned),
            context=PRIME_SENTINEL_PQ_CONTEXT,
        )
    except UnsupportedAlgorithm as exc:
        raise PrimeSentinelPoOIssuanceStoreError("ML-DSA-65 signing backend unavailable") from exc
    signed = unsigned.model_copy(
        update={
            "signature_b64url": base64.urlsafe_b64encode(signature)
            .rstrip(b"=")
            .decode("ascii")
        }
    )
    persisted = store.mark_signed(
        request_id=request_id,
        signature_b64url=signed.signature_b64url,
        assertion=signed.model_dump(mode="json"),
    )
    stored = persisted.assertion_dict()
    if stored is None:
        raise PrimeSentinelPoOIssuanceStoreError(
            "durable SIGNED PQ PoO issuance record is missing its assertion"
        )
    return PrimeSentinelPqPoOAuthorizationAssertion.model_validate(stored)


def create_prime_sentinel_pq_poo_app() -> FastAPI:
    signer = PrimeSentinelPqSigner.from_environment()
    try:
        store = PrimeSentinelPoOIssuanceStore.from_environment()
    except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
        raise PrimeSentinelServiceConfigError(str(exc)) from exc
    _bind_poo_signing_key_identity(store, signer)

    app = FastAPI(
        title="Worldshepherd PRIME SENTINEL PQ PoO Authorization Service",
        version="1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.signer = signer
    app.state.poo_issuance_store = store

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    @app.get("/readyz")
    def health() -> dict[str, Any]:
        try:
            status = store.health()
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="PQ PoO issuance ledger unavailable") from exc
        if not status.get("ok"):
            raise HTTPException(status_code=503, detail="PQ PoO issuance ledger integrity check failed")
        return {
            "ok": True,
            "service": "PRIME_SENTINEL_PQ_POO",
            "algorithm": PRIME_SENTINEL_PQ_ALGORITHM,
            "standard": PRIME_SENTINEL_PQ_STANDARD,
            "key_id": signer.key_id,
        }

    @app.get("/v1/public-key", response_model=PrimeSentinelPqPublicKey)
    def public_key() -> PrimeSentinelPqPublicKey:
        return signer.public_key_record()

    @app.post(
        "/v1/poo-technical-state-commit",
        response_model=PrimeSentinelPqPoOIssueResponse,
    )
    def issue_pq_poo_technical_state_commit(
        body: PrimeSentinelPoOIssueRequest,
        request: Request,
    ) -> PrimeSentinelPqPoOIssueResponse:
        _require_bearer(request, signer.service_token)
        request_id = _require_request_id(request)
        try:
            assertion = _issue_pq_durable(
                signer,
                store,
                body,
                request_id=request_id,
            )
        except PrimeSentinelPoORequestConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PrimeSentinelPoOLedgerFull as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="PQ PoO issuance persistence failed") from exc
        return PrimeSentinelPqPoOIssueResponse(assertion=assertion)

    return app
