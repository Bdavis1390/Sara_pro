from __future__ import annotations

import base64
import sqlite3
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_SCHEMA,
    PrimeSentinelPoOAuthorizationAssertion,
    canonical_poo_authorization_message,
)
from .prime_sentinel_poo_issuance_store import (
    PoOIssuanceRecord,
    PrimeSentinelPoOIssuanceStore,
    PrimeSentinelPoOIssuanceStoreError,
    PrimeSentinelPoOLedgerFull,
    PrimeSentinelPoORequestConflict,
    parse_utc,
)
from .prime_sentinel_service import (
    PrimeSentinelServiceConfigError,
    _require_bearer,
    _require_request_id,
    create_prime_sentinel_app,
)


class PrimeSentinelPoOIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=256)
    governance_projection_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_decision_digest: str = Field(min_length=1, max_length=256)
    expected_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_state_digest: str = Field(min_length=1, max_length=256)
    lifetime_seconds: int = Field(default=300, ge=1, le=900)


class PrimeSentinelPoOIssueResponse(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-POO-ISSUE-RESPONSE-V1"
    assertion: PrimeSentinelPoOAuthorizationAssertion


class PrimeSentinelPoOIssuanceStatus(BaseModel):
    schema: str = "WS-PRIME-SENTINEL-POO-ISSUANCE-STATUS-V1"
    request_id: str
    state: str
    authorization_id: str
    asset_id: str
    governance_projection_digest: str
    source_decision_digest: str
    expected_registry_digest: str
    candidate_registry_digest: str
    candidate_state_digest: str
    key_id: str
    key_fingerprint_sha256: str
    issued_at: str
    expires_at: str
    prepared_at: str
    signed_at: str | None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _bind_poo_signing_key_identity(store: PrimeSentinelPoOIssuanceStore, signer: Any) -> None:
    name = f"signing_key_fingerprint:{signer.key_id}"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(store.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT value FROM metadata WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO metadata(name, value) VALUES(?, ?)",
                (name, signer.fingerprint_sha256),
            )
        elif row["value"] != signer.fingerprint_sha256:
            raise PrimeSentinelServiceConfigError(
                "PRIME SENTINEL PoO signing key ID is already bound to different key material"
            )
        connection.commit()
    except sqlite3.Error as exc:
        raise PrimeSentinelServiceConfigError(
            "unable to bind PRIME SENTINEL signing key identity to PoO issuance ledger"
        ) from exc
    finally:
        if connection is not None:
            connection.close()


def _poo_assertion_from_record(
    record: PoOIssuanceRecord,
    *,
    signature_b64url: str,
) -> PrimeSentinelPoOAuthorizationAssertion:
    return PrimeSentinelPoOAuthorizationAssertion(
        schema=PRIME_SENTINEL_POO_AUTHZ_SCHEMA,
        issuer="PRIME_SENTINEL",
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


def _issue_poo_durable(
    signer: Any,
    store: PrimeSentinelPoOIssuanceStore,
    body: PrimeSentinelPoOIssueRequest,
    *,
    request_id: str,
) -> PrimeSentinelPoOAuthorizationAssertion:
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
                "SIGNED PoO issuance record is missing its assertion"
            )
        return PrimeSentinelPoOAuthorizationAssertion.model_validate(stored)

    unsigned = _poo_assertion_from_record(record, signature_b64url="UNSIGNED")
    signature = signer._private_key.sign(canonical_poo_authorization_message(unsigned))
    signed = unsigned.model_copy(update={"signature_b64url": _b64url(signature)})
    persisted = store.mark_signed(
        request_id=request_id,
        signature_b64url=signed.signature_b64url,
        assertion=signed.model_dump(mode="json"),
    )
    stored = persisted.assertion_dict()
    if stored is None:
        raise PrimeSentinelPoOIssuanceStoreError(
            "durable SIGNED PoO issuance record is missing its assertion"
        )
    return PrimeSentinelPoOAuthorizationAssertion.model_validate(stored)


def _status_from_record(record: PoOIssuanceRecord, signer: Any) -> PrimeSentinelPoOIssuanceStatus:
    return PrimeSentinelPoOIssuanceStatus(
        request_id=record.request_id,
        state=record.state,
        authorization_id=record.authorization_id,
        asset_id=record.asset_id,
        governance_projection_digest=record.governance_projection_digest,
        source_decision_digest=record.source_decision_digest,
        expected_registry_digest=record.expected_registry_digest,
        candidate_registry_digest=record.candidate_registry_digest,
        candidate_state_digest=record.candidate_state_digest,
        key_id=record.key_id,
        key_fingerprint_sha256=signer.fingerprint_sha256,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        prepared_at=record.prepared_at,
        signed_at=record.signed_at,
    )


def create_prime_sentinel_poo_app():
    app = create_prime_sentinel_app()
    signer = app.state.signer
    try:
        poo_store = PrimeSentinelPoOIssuanceStore.from_environment()
    except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
        raise PrimeSentinelServiceConfigError(str(exc)) from exc
    _bind_poo_signing_key_identity(poo_store, signer)
    app.state.poo_issuance_store = poo_store

    @app.get("/v1/poo-ledger-status")
    def poo_ledger_status(request: Request) -> dict[str, object]:
        _require_bearer(request, signer.service_token)
        try:
            status = poo_store.health()
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="PoO issuance ledger unavailable") from exc
        if not status["ok"]:
            raise HTTPException(status_code=503, detail="PoO issuance ledger integrity check failed")
        return {"schema": "WS-PRIME-SENTINEL-POO-LEDGER-STATUS-V1", **status}

    @app.get(
        "/v1/poo-issuance/{request_id}",
        response_model=PrimeSentinelPoOIssuanceStatus,
    )
    def poo_issuance_status(
        request_id: str,
        request: Request,
    ) -> PrimeSentinelPoOIssuanceStatus:
        _require_bearer(request, signer.service_token)
        try:
            record = poo_store.get(request_id)
            if record is None:
                raise HTTPException(status_code=404, detail="PoO issuance request not found")
            return _status_from_record(record, signer)
        except HTTPException:
            raise
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="PoO issuance ledger unavailable") from exc

    @app.post(
        "/v1/poo-technical-state-commit",
        response_model=PrimeSentinelPoOIssueResponse,
    )
    def issue_poo_technical_state_commit(
        body: PrimeSentinelPoOIssueRequest,
        request: Request,
    ) -> PrimeSentinelPoOIssueResponse:
        _require_bearer(request, signer.service_token)
        request_id = _require_request_id(request)
        try:
            assertion = _issue_poo_durable(
                signer,
                poo_store,
                body,
                request_id=request_id,
            )
        except PrimeSentinelPoORequestConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PrimeSentinelPoOLedgerFull as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error) as exc:
            raise HTTPException(status_code=503, detail="PoO issuance persistence failed") from exc
        return PrimeSentinelPoOIssueResponse(assertion=assertion)

    return app
