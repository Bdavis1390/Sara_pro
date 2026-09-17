from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .event_outbox import queue_event_outbox_patch
from .poo_prime_quorum_commit import (
    POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA,
    PoOPrimeQuorumCommitError,
    PoOPrimeQuorumCommitRequest,
    PoOPrimeQuorumCommitResult,
    prepare_prime_quorum_poo_commit_patch,
)
from .poo_registry_commit import PoODurableCommitRequest
from .prime_sentinel_poo_authorization import (
    PrimeSentinelPoOAuthorizationAssertion,
    PrimeSentinelPoOVerifier,
)
from .prime_sentinel_pq_poo_authorization import (
    PRIME_SENTINEL_PQ_ALGORITHM,
    PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY,
    PRIME_SENTINEL_PQ_STANDARD,
    PrimeSentinelPqPoOAuthorizationAssertion,
    PrimeSentinelPqPoOAuthorizationError,
    PrimeSentinelPqPoOVerifier,
    VerifiedPrimeSentinelPqPoOAuthorization,
    consumed_pq_poo_authorization_registry_patch,
    signed_pq_poo_authorization_fingerprint,
)


POO_PRIME_HYBRID_PQ_COMMIT_REQUEST_SCHEMA = "WS-POO-PRIME-HYBRID-PQ-DURABLE-COMMIT-REQUEST-V1"
POO_PRIME_HYBRID_PQ_CLAIMS_BOUNDARY = (
    "HYBRID_ED25519_QUORUM_PLUS_FIPS204_MLDSA65_INTERNAL_TECHNICAL_STATE_"
    "COMMIT_NOT_LEGAL_TITLE_OR_LIVE_VALUE_AUTHORITY"
)
MAX_PQ_AUTHORIZATIONS = 64


class PoOPrimeHybridPqCommitError(ValueError):
    pass


class PoOPrimeHybridPqCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_PRIME_HYBRID_PQ_COMMIT_REQUEST_SCHEMA] = (
        POO_PRIME_HYBRID_PQ_COMMIT_REQUEST_SCHEMA
    )
    durable_commit: PoODurableCommitRequest
    prime_authorizations: list[PrimeSentinelPoOAuthorizationAssertion]
    pq_authorization: PrimeSentinelPqPoOAuthorizationAssertion

    @model_validator(mode="after")
    def require_separate_pq_identity(self) -> "PoOPrimeHybridPqCommitRequest":
        classical_key_ids = {item.key_id for item in self.prime_authorizations}
        classical_authorization_ids = {
            item.authorization_id for item in self.prime_authorizations
        }
        classical_nonces = {item.nonce for item in self.prime_authorizations}
        if self.pq_authorization.key_id in classical_key_ids:
            raise ValueError("PQ authorization key ID must be distinct from classical quorum key IDs")
        if self.pq_authorization.authorization_id in classical_authorization_ids:
            raise ValueError("PQ authorization ID must be distinct from classical authorization IDs")
        if self.pq_authorization.nonce in classical_nonces:
            raise ValueError("PQ authorization nonce must be distinct from classical authorization nonces")
        return self


class PoOPrimeHybridPqCommitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["COMMITTED", "ALREADY_COMMITTED"]
    commit_id: str
    registry_digest: str
    candidate_state_digest: str
    projection_digest: str
    audit_event_id: str
    prime_quorum_audit_event_id: str
    hybrid_pq_audit_event_id: str
    approval_reference: str
    approved_actor: str
    classical_quorum_threshold: int
    classical_quorum_size: int
    classical_authorization_ids: list[str]
    classical_signing_key_ids: list[str]
    pq_authorization_id: str
    pq_signing_key_id: str
    pq_signing_key_fingerprint_sha256: str
    pq_algorithm: Literal[PRIME_SENTINEL_PQ_ALGORITHM] = PRIME_SENTINEL_PQ_ALGORITHM
    pq_standard: Literal[PRIME_SENTINEL_PQ_STANDARD] = PRIME_SENTINEL_PQ_STANDARD
    durable_internal_state_committed: Literal[True] = True
    classical_quorum_cryptographic_authorization_verified: Literal[True] = True
    pq_cryptographic_authorization_verified: Literal[True] = True
    hybrid_cryptographic_authorization_verified: Literal[True] = True
    single_classical_signer_sufficient: Literal[False] = False
    pq_only_sufficient: Literal[False] = False
    algorithm_downgrade_permitted: Literal[False] = False
    legal_title_changed: Literal[False] = False
    live_value_moved: Literal[False] = False
    credential_rotated: Literal[False] = False
    external_transfer_executed: Literal[False] = False


def _scope_from_quorum(result: PoOPrimeQuorumCommitResult, body: PoOPrimeHybridPqCommitRequest) -> dict[str, str]:
    projection = body.durable_commit.governance_projection.model_dump(mode="json")
    return {
        "asset_id": projection["asset_id"],
        "governance_projection_digest": result.projection_digest,
        "source_decision_digest": projection["source_digest"],
        "expected_registry_digest": projection["expected_registry_digest"],
        "candidate_registry_digest": result.registry_digest,
        "candidate_state_digest": result.candidate_state_digest,
    }


def _assert_pq_scope(
    verified: VerifiedPrimeSentinelPqPoOAuthorization,
    *,
    expected: dict[str, str],
) -> None:
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
        raise PoOPrimeHybridPqCommitError(
            "PQ authorization scope mismatch: " + ", ".join(sorted(mismatches))
        )


def _stored_exact_pq_authorization(
    registry: dict[str, Any],
    *,
    assertion: PrimeSentinelPqPoOAuthorizationAssertion,
    expected: dict[str, str],
    commit_id: str,
) -> VerifiedPrimeSentinelPqPoOAuthorization:
    raw = registry.get(PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PoOPrimeHybridPqCommitError("stored PQ authorization registry is malformed")
    entry = raw.get(assertion.authorization_id)
    if not isinstance(entry, dict):
        raise PoOPrimeHybridPqCommitError(
            "already-committed PoO state is missing its consumed PQ authorization"
        )
    required = {
        "status": "CONSUMED",
        "commit_id": commit_id,
        **expected,
        "signed_assertion_sha256": signed_pq_poo_authorization_fingerprint(assertion),
        "key_id": assertion.key_id,
        "nonce": assertion.nonce,
        "algorithm": PRIME_SENTINEL_PQ_ALGORITHM,
        "standard": PRIME_SENTINEL_PQ_STANDARD,
    }
    mismatches = [name for name, value in required.items() if entry.get(name) != value]
    if mismatches:
        raise PoOPrimeHybridPqCommitError(
            "stored PQ authorization does not match exact committed hybrid request: "
            + ", ".join(sorted(mismatches))
        )
    return VerifiedPrimeSentinelPqPoOAuthorization(
        authorization_id=assertion.authorization_id,
        asset_id=assertion.asset_id,
        governance_projection_digest=assertion.governance_projection_digest,
        source_decision_digest=assertion.source_decision_digest,
        expected_registry_digest=assertion.expected_registry_digest,
        candidate_registry_digest=assertion.candidate_registry_digest,
        candidate_state_digest=assertion.candidate_state_digest,
        key_id=assertion.key_id,
        key_fingerprint_sha256=str(entry.get("key_fingerprint_sha256", "")),
        signed_assertion_sha256=signed_pq_poo_authorization_fingerprint(assertion),
        nonce=assertion.nonce,
        issued_at=assertion.issued_at,
        expires_at=assertion.expires_at,
    )


def _hybrid_result(
    classical: PoOPrimeQuorumCommitResult,
    pq: VerifiedPrimeSentinelPqPoOAuthorization,
) -> PoOPrimeHybridPqCommitResult:
    return PoOPrimeHybridPqCommitResult(
        status=classical.status,
        commit_id=classical.commit_id,
        registry_digest=classical.registry_digest,
        candidate_state_digest=classical.candidate_state_digest,
        projection_digest=classical.projection_digest,
        audit_event_id=classical.audit_event_id,
        prime_quorum_audit_event_id=classical.prime_quorum_audit_event_id,
        hybrid_pq_audit_event_id=f"SARA-EVENT-PRIME-HYBRID-PQ-{classical.commit_id}",
        approval_reference=classical.approval_reference,
        approved_actor=classical.approved_actor,
        classical_quorum_threshold=classical.quorum_threshold,
        classical_quorum_size=classical.quorum_size,
        classical_authorization_ids=classical.prime_authorization_ids,
        classical_signing_key_ids=classical.prime_signing_key_ids,
        pq_authorization_id=pq.authorization_id,
        pq_signing_key_id=pq.key_id,
        pq_signing_key_fingerprint_sha256=pq.key_fingerprint_sha256,
    )


def prepare_prime_hybrid_pq_poo_commit_patch(
    registry: dict[str, Any],
    body: PoOPrimeHybridPqCommitRequest,
    *,
    actor: str,
    classical_verifier: PrimeSentinelPoOVerifier,
    pq_verifier: PrimeSentinelPqPoOVerifier,
    classical_threshold: int,
    committed_at: str | None = None,
) -> tuple[dict[str, Any] | None, PoOPrimeHybridPqCommitResult]:
    try:
        classical_body = PoOPrimeQuorumCommitRequest(
            schema=POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA,
            durable_commit=body.durable_commit,
            prime_authorizations=body.prime_authorizations,
        )
        classical_patch, classical_result = prepare_prime_quorum_poo_commit_patch(
            registry,
            classical_body,
            actor=actor,
            verifier=classical_verifier,
            threshold=classical_threshold,
            committed_at=committed_at,
        )
    except (ValueError, PoOPrimeQuorumCommitError) as exc:
        raise PoOPrimeHybridPqCommitError(str(exc)) from exc

    expected = _scope_from_quorum(classical_result, body)
    if classical_patch is None:
        pq_verified = _stored_exact_pq_authorization(
            registry,
            assertion=body.pq_authorization,
            expected=expected,
            commit_id=classical_result.commit_id,
        )
        return None, _hybrid_result(classical_result, pq_verified)

    try:
        pq_verified = pq_verifier.verify(body.pq_authorization)
    except PrimeSentinelPqPoOAuthorizationError as exc:
        raise PoOPrimeHybridPqCommitError(str(exc)) from exc
    _assert_pq_scope(pq_verified, expected=expected)

    raw_pq = registry.get(PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw_pq, dict):
        raise PoOPrimeHybridPqCommitError("stored PQ authorization registry is malformed")
    if len(raw_pq) + 1 > MAX_PQ_AUTHORIZATIONS:
        raise PoOPrimeHybridPqCommitError("PQ PoO authorization registry capacity reached")

    working = dict(registry)
    working.update(classical_patch)
    try:
        pq_patch = consumed_pq_poo_authorization_registry_patch(
            working,
            verified=pq_verified,
            commit_id=classical_result.commit_id,
        )
    except PrimeSentinelPqPoOAuthorizationError as exc:
        raise PoOPrimeHybridPqCommitError(str(exc)) from exc
    working.update(pq_patch)

    hybrid_event_id = f"SARA-EVENT-PRIME-HYBRID-PQ-{classical_result.commit_id}"
    hybrid_event_patch, actual_event_id = queue_event_outbox_patch(
        working,
        event="prime_sentinel_poo_hybrid_pq_authorization_consumed",
        actor=actor,
        event_id=hybrid_event_id,
        payload={
            "commit_id": classical_result.commit_id,
            **expected,
            "classical_quorum_threshold": classical_result.quorum_threshold,
            "classical_quorum_size": classical_result.quorum_size,
            "classical_authorization_ids": classical_result.prime_authorization_ids,
            "classical_key_ids": classical_result.prime_signing_key_ids,
            "pq_authorization_id": pq_verified.authorization_id,
            "pq_key_id": pq_verified.key_id,
            "pq_key_fingerprint_sha256": pq_verified.key_fingerprint_sha256,
            "pq_signed_assertion_sha256": pq_verified.signed_assertion_sha256,
            "pq_algorithm": PRIME_SENTINEL_PQ_ALGORITHM,
            "pq_standard": PRIME_SENTINEL_PQ_STANDARD,
            "classical_quorum_cryptographic_authorization_verified": True,
            "pq_cryptographic_authorization_verified": True,
            "hybrid_cryptographic_authorization_verified": True,
            "single_classical_signer_sufficient": False,
            "pq_only_sufficient": False,
            "algorithm_downgrade_permitted": False,
            "durable_internal_state_committed": True,
            "legal_title_changed": False,
            "live_value_moved": False,
            "credential_rotated": False,
            "external_transfer_executed": False,
            "claims_boundary": POO_PRIME_HYBRID_PQ_CLAIMS_BOUNDARY,
        },
    )
    if actual_event_id != hybrid_event_id:
        raise PoOPrimeHybridPqCommitError("hybrid PQ audit event ID changed unexpectedly")

    patch = dict(classical_patch)
    patch[PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY] = working[
        PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY
    ]
    patch.update(hybrid_event_patch)
    return patch, _hybrid_result(classical_result, pq_verified)
