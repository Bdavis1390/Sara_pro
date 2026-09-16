from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .event_outbox import queue_event_outbox_patch
from .poo_registry_commit import (
    PoODurableCommitError,
    PoODurableCommitRequest,
    PoODurableCommitResult,
    prepare_poo_durable_commit_patch,
)
from .prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
    PrimeSentinelPoOAuthorizationAssertion,
    PrimeSentinelPoOAuthorizationError,
    PrimeSentinelPoOVerifier,
    VerifiedPrimeSentinelPoOAuthorization,
    consumed_poo_authorization_registry_patch,
)


POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA = (
    "WS-POO-PRIME-AUTHORIZED-DURABLE-COMMIT-REQUEST-V1"
)
POO_PRIME_AUTHORIZED_CLAIM_BOUNDARY = (
    "PRIME_SIGNED_INTERNAL_TECHNICAL_STATE_COMMIT_NOT_LEGAL_TITLE_OR_LIVE_VALUE_AUTHORITY"
)
MAX_POO_PRIME_AUTHORIZATIONS = 64


class PoOPrimeAuthorizedCommitError(ValueError):
    pass


class PoOPrimeAuthorizedCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA] = (
        POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA
    )
    durable_commit: PoODurableCommitRequest
    prime_authorization: PrimeSentinelPoOAuthorizationAssertion


class PoOPrimeAuthorizedCommitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["COMMITTED", "ALREADY_COMMITTED"]
    commit_id: str
    registry_digest: str
    candidate_state_digest: str
    projection_digest: str
    audit_event_id: str
    prime_authorization_audit_event_id: str
    approval_reference: str
    approved_actor: str
    prime_authorization_id: str
    prime_signing_key_id: str
    prime_signing_key_fingerprint_sha256: str
    durable_internal_state_committed: Literal[True] = True
    prime_cryptographic_authorization_verified: Literal[True] = True
    legal_title_changed: Literal[False] = False
    live_value_moved: Literal[False] = False
    credential_rotated: Literal[False] = False
    external_transfer_executed: Literal[False] = False


def _projection(body: PoOPrimeAuthorizedCommitRequest) -> dict[str, Any]:
    return body.durable_commit.governance_projection.model_dump(mode="json")


def _assert_scope_matches(
    verified: VerifiedPrimeSentinelPoOAuthorization,
    *,
    projection: dict[str, Any],
    result: PoODurableCommitResult,
) -> None:
    expected = {
        "asset_id": projection["asset_id"],
        "governance_projection_digest": result.projection_digest,
        "source_decision_digest": projection["source_digest"],
        "expected_registry_digest": projection["expected_registry_digest"],
        "candidate_registry_digest": result.registry_digest,
        "candidate_state_digest": result.candidate_state_digest,
    }
    actual = {
        "asset_id": verified.asset_id,
        "governance_projection_digest": verified.governance_projection_digest,
        "source_decision_digest": verified.source_decision_digest,
        "expected_registry_digest": verified.expected_registry_digest,
        "candidate_registry_digest": verified.candidate_registry_digest,
        "candidate_state_digest": verified.candidate_state_digest,
    }
    mismatches = [name for name, value in expected.items() if actual[name] != value]
    if mismatches:
        raise PoOPrimeAuthorizedCommitError(
            "PRIME PoO authorization scope mismatch: " + ", ".join(sorted(mismatches))
        )


def _stored_exact_authorization(
    registry: dict[str, Any],
    *,
    assertion: PrimeSentinelPoOAuthorizationAssertion,
    projection: dict[str, Any],
    result: PoODurableCommitResult,
) -> dict[str, Any]:
    raw = registry.get(PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PoOPrimeAuthorizedCommitError("stored PRIME PoO authorization registry is malformed")
    entry = raw.get(assertion.authorization_id)
    if not isinstance(entry, dict):
        raise PoOPrimeAuthorizedCommitError(
            "already-committed PoO state is missing its consumed PRIME authorization"
        )
    expected = {
        "status": "CONSUMED",
        "commit_id": result.commit_id,
        "asset_id": projection["asset_id"],
        "governance_projection_digest": result.projection_digest,
        "source_decision_digest": projection["source_digest"],
        "expected_registry_digest": projection["expected_registry_digest"],
        "candidate_registry_digest": result.registry_digest,
        "candidate_state_digest": result.candidate_state_digest,
        "key_id": assertion.key_id,
        "nonce": assertion.nonce,
    }
    mismatches = [name for name, value in expected.items() if entry.get(name) != value]
    if mismatches:
        raise PoOPrimeAuthorizedCommitError(
            "stored PRIME PoO authorization does not match exact committed request: "
            + ", ".join(sorted(mismatches))
        )
    return entry


def _result(
    base: PoODurableCommitResult,
    *,
    assertion: PrimeSentinelPoOAuthorizationAssertion,
    key_fingerprint: str,
) -> PoOPrimeAuthorizedCommitResult:
    return PoOPrimeAuthorizedCommitResult(
        status=base.status,
        commit_id=base.commit_id,
        registry_digest=base.registry_digest,
        candidate_state_digest=base.candidate_state_digest,
        projection_digest=base.projection_digest,
        audit_event_id=base.audit_event_id,
        prime_authorization_audit_event_id=f"SARA-EVENT-PRIME-AUTH-{base.commit_id}",
        approval_reference=base.approval_reference,
        approved_actor=base.approved_actor,
        prime_authorization_id=assertion.authorization_id,
        prime_signing_key_id=assertion.key_id,
        prime_signing_key_fingerprint_sha256=key_fingerprint,
    )


def prepare_prime_authorized_poo_commit_patch(
    registry: dict[str, Any],
    body: PoOPrimeAuthorizedCommitRequest,
    *,
    actor: str,
    verifier: PrimeSentinelPoOVerifier,
    committed_at: str | None = None,
) -> tuple[dict[str, Any] | None, PoOPrimeAuthorizedCommitResult]:
    projection = _projection(body)

    base_patch, base_result = prepare_poo_durable_commit_patch(
        registry,
        body.durable_commit,
        actor=actor,
        committed_at=committed_at,
    )

    if base_patch is None:
        entry = _stored_exact_authorization(
            registry,
            assertion=body.prime_authorization,
            projection=projection,
            result=base_result,
        )
        return None, _result(
            base_result,
            assertion=body.prime_authorization,
            key_fingerprint=str(entry.get("key_fingerprint_sha256", "")),
        )

    try:
        verified = verifier.verify(body.prime_authorization)
    except PrimeSentinelPoOAuthorizationError as exc:
        raise PoOPrimeAuthorizedCommitError(str(exc)) from exc
    _assert_scope_matches(verified, projection=projection, result=base_result)

    raw_authorizations = registry.get(PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw_authorizations, dict):
        raise PoOPrimeAuthorizedCommitError("stored PRIME PoO authorization registry is malformed")
    if len(raw_authorizations) >= MAX_POO_PRIME_AUTHORIZATIONS:
        raise PoOPrimeAuthorizedCommitError("PRIME PoO authorization registry capacity reached")

    working = dict(registry)
    working.update(base_patch)
    try:
        auth_patch = consumed_poo_authorization_registry_patch(
            working,
            verified=verified,
            commit_id=base_result.commit_id,
        )
    except PrimeSentinelPoOAuthorizationError as exc:
        raise PoOPrimeAuthorizedCommitError(str(exc)) from exc
    working.update(auth_patch)

    prime_audit_event_id = f"SARA-EVENT-PRIME-AUTH-{base_result.commit_id}"
    prime_event_patch, actual_event_id = queue_event_outbox_patch(
        working,
        event="prime_sentinel_poo_authorization_consumed",
        actor=actor,
        event_id=prime_audit_event_id,
        payload={
            "commit_id": base_result.commit_id,
            "authorization_id": verified.authorization_id,
            "key_id": verified.key_id,
            "key_fingerprint_sha256": verified.key_fingerprint_sha256,
            "asset_id": verified.asset_id,
            "governance_projection_digest": verified.governance_projection_digest,
            "source_decision_digest": verified.source_decision_digest,
            "expected_registry_digest": verified.expected_registry_digest,
            "candidate_registry_digest": verified.candidate_registry_digest,
            "candidate_state_digest": verified.candidate_state_digest,
            "prime_cryptographic_authorization_verified": True,
            "durable_internal_state_committed": True,
            "legal_title_changed": False,
            "live_value_moved": False,
            "credential_rotated": False,
            "external_transfer_executed": False,
            "claims_boundary": POO_PRIME_AUTHORIZED_CLAIM_BOUNDARY,
        },
    )
    if actual_event_id != prime_audit_event_id:
        raise PoOPrimeAuthorizedCommitError("PRIME PoO audit event ID changed unexpectedly")

    patch = dict(base_patch)
    patch.update(auth_patch)
    patch.update(prime_event_patch)
    return patch, _result(
        base_result,
        assertion=body.prime_authorization,
        key_fingerprint=verified.key_fingerprint_sha256,
    )
