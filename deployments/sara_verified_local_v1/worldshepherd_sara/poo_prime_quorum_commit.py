from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    signed_poo_authorization_fingerprint,
)


POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA = "WS-POO-PRIME-QUORUM-DURABLE-COMMIT-REQUEST-V1"
POO_PRIME_QUORUM_CLAIMS_BOUNDARY = (
    "PRIME_MULTI_KEY_QUORUM_INTERNAL_TECHNICAL_STATE_COMMIT_NOT_LEGAL_TITLE_OR_"
    "LIVE_VALUE_AUTHORITY"
)
MAX_QUORUM_SIZE = 8


class PoOPrimeQuorumCommitError(ValueError):
    pass


class PoOPrimeQuorumCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA] = POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA
    durable_commit: PoODurableCommitRequest
    prime_authorizations: list[PrimeSentinelPoOAuthorizationAssertion] = Field(
        min_length=2,
        max_length=MAX_QUORUM_SIZE,
    )

    @model_validator(mode="after")
    def distinct_assertion_identities(self) -> "PoOPrimeQuorumCommitRequest":
        key_ids = [item.key_id for item in self.prime_authorizations]
        authorization_ids = [item.authorization_id for item in self.prime_authorizations]
        nonces = [item.nonce for item in self.prime_authorizations]
        if len(set(key_ids)) != len(key_ids):
            raise ValueError("PRIME quorum requires distinct signing key IDs")
        if len(set(authorization_ids)) != len(authorization_ids):
            raise ValueError("PRIME quorum requires distinct authorization IDs")
        if len(set(nonces)) != len(nonces):
            raise ValueError("PRIME quorum requires distinct authorization nonces")
        return self


class PoOPrimeQuorumCommitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["COMMITTED", "ALREADY_COMMITTED"]
    commit_id: str
    registry_digest: str
    candidate_state_digest: str
    projection_digest: str
    audit_event_id: str
    prime_quorum_audit_event_id: str
    approval_reference: str
    approved_actor: str
    quorum_threshold: int
    quorum_size: int
    prime_authorization_ids: list[str]
    prime_signing_key_ids: list[str]
    prime_signing_key_fingerprints_sha256: list[str]
    durable_internal_state_committed: Literal[True] = True
    prime_quorum_cryptographic_authorization_verified: Literal[True] = True
    single_signer_sufficient: Literal[False] = False
    legal_title_changed: Literal[False] = False
    live_value_moved: Literal[False] = False
    credential_rotated: Literal[False] = False
    external_transfer_executed: Literal[False] = False


def _projection(body: PoOPrimeQuorumCommitRequest) -> dict[str, Any]:
    return body.durable_commit.governance_projection.model_dump(mode="json")


def _expected_scope(
    *,
    projection: dict[str, Any],
    result: PoODurableCommitResult,
) -> dict[str, str]:
    return {
        "asset_id": projection["asset_id"],
        "governance_projection_digest": result.projection_digest,
        "source_decision_digest": projection["source_digest"],
        "expected_registry_digest": projection["expected_registry_digest"],
        "candidate_registry_digest": result.registry_digest,
        "candidate_state_digest": result.candidate_state_digest,
    }


def _assert_scope_matches(
    verified: VerifiedPrimeSentinelPoOAuthorization,
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
        raise PoOPrimeQuorumCommitError(
            "PRIME quorum authorization scope mismatch: " + ", ".join(sorted(mismatches))
        )


def _stored_exact_authorization(
    registry: dict[str, Any],
    *,
    assertion: PrimeSentinelPoOAuthorizationAssertion,
    expected: dict[str, str],
    commit_id: str,
) -> dict[str, Any]:
    raw = registry.get(PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PoOPrimeQuorumCommitError("stored PRIME PoO authorization registry is malformed")
    entry = raw.get(assertion.authorization_id)
    if not isinstance(entry, dict):
        raise PoOPrimeQuorumCommitError(
            "already-committed PoO state is missing a consumed PRIME quorum authorization"
        )
    required = {
        "status": "CONSUMED",
        "commit_id": commit_id,
        **expected,
        "signed_assertion_sha256": signed_poo_authorization_fingerprint(assertion),
        "key_id": assertion.key_id,
        "nonce": assertion.nonce,
    }
    mismatches = [name for name, value in required.items() if entry.get(name) != value]
    if mismatches:
        raise PoOPrimeQuorumCommitError(
            "stored PRIME quorum authorization does not match exact committed request: "
            + ", ".join(sorted(mismatches))
        )
    return entry


def _sorted_verified(
    verified: list[VerifiedPrimeSentinelPoOAuthorization],
) -> list[VerifiedPrimeSentinelPoOAuthorization]:
    return sorted(verified, key=lambda item: (item.key_id, item.authorization_id))


def _result(
    base: PoODurableCommitResult,
    *,
    threshold: int,
    verified: list[VerifiedPrimeSentinelPoOAuthorization],
) -> PoOPrimeQuorumCommitResult:
    ordered = _sorted_verified(verified)
    return PoOPrimeQuorumCommitResult(
        status=base.status,
        commit_id=base.commit_id,
        registry_digest=base.registry_digest,
        candidate_state_digest=base.candidate_state_digest,
        projection_digest=base.projection_digest,
        audit_event_id=base.audit_event_id,
        prime_quorum_audit_event_id=f"SARA-EVENT-PRIME-QUORUM-{base.commit_id}",
        approval_reference=base.approval_reference,
        approved_actor=base.approved_actor,
        quorum_threshold=threshold,
        quorum_size=len(ordered),
        prime_authorization_ids=[item.authorization_id for item in ordered],
        prime_signing_key_ids=[item.key_id for item in ordered],
        prime_signing_key_fingerprints_sha256=[
            item.key_fingerprint_sha256 for item in ordered
        ],
    )


def prepare_prime_quorum_poo_commit_patch(
    registry: dict[str, Any],
    body: PoOPrimeQuorumCommitRequest,
    *,
    actor: str,
    verifier: PrimeSentinelPoOVerifier,
    threshold: int,
    committed_at: str | None = None,
) -> tuple[dict[str, Any] | None, PoOPrimeQuorumCommitResult]:
    if threshold < 2 or threshold > MAX_QUORUM_SIZE:
        raise PoOPrimeQuorumCommitError(
            f"PRIME quorum threshold must be between 2 and {MAX_QUORUM_SIZE}"
        )
    if len(body.prime_authorizations) != threshold:
        raise PoOPrimeQuorumCommitError(
            "presented PRIME authorization count must exactly equal configured quorum threshold"
        )

    projection = _projection(body)
    base_patch, base_result = prepare_poo_durable_commit_patch(
        registry,
        body.durable_commit,
        actor=actor,
        committed_at=committed_at,
    )
    expected = _expected_scope(projection=projection, result=base_result)

    if base_patch is None:
        replay_verified: list[VerifiedPrimeSentinelPoOAuthorization] = []
        for assertion in body.prime_authorizations:
            entry = _stored_exact_authorization(
                registry,
                assertion=assertion,
                expected=expected,
                commit_id=base_result.commit_id,
            )
            replay_verified.append(
                VerifiedPrimeSentinelPoOAuthorization(
                    authorization_id=assertion.authorization_id,
                    asset_id=assertion.asset_id,
                    governance_projection_digest=assertion.governance_projection_digest,
                    source_decision_digest=assertion.source_decision_digest,
                    expected_registry_digest=assertion.expected_registry_digest,
                    candidate_registry_digest=assertion.candidate_registry_digest,
                    candidate_state_digest=assertion.candidate_state_digest,
                    key_id=assertion.key_id,
                    key_fingerprint_sha256=str(entry.get("key_fingerprint_sha256", "")),
                    signed_assertion_sha256=signed_poo_authorization_fingerprint(assertion),
                    nonce=assertion.nonce,
                    issued_at=assertion.issued_at,
                    expires_at=assertion.expires_at,
                )
            )
        return None, _result(base_result, threshold=threshold, verified=replay_verified)

    verified_assertions: list[VerifiedPrimeSentinelPoOAuthorization] = []
    for assertion in body.prime_authorizations:
        try:
            verified = verifier.verify(assertion)
        except PrimeSentinelPoOAuthorizationError as exc:
            raise PoOPrimeQuorumCommitError(str(exc)) from exc
        _assert_scope_matches(verified, expected=expected)
        verified_assertions.append(verified)

    if len({item.key_id for item in verified_assertions}) != threshold:
        raise PoOPrimeQuorumCommitError("verified PRIME quorum does not contain distinct signing keys")

    raw_authorizations = registry.get(PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw_authorizations, dict):
        raise PoOPrimeQuorumCommitError("stored PRIME PoO authorization registry is malformed")
    if len(raw_authorizations) + threshold > 64:
        raise PoOPrimeQuorumCommitError("PRIME PoO authorization registry capacity reached")

    working = dict(registry)
    working.update(base_patch)
    for verified in _sorted_verified(verified_assertions):
        try:
            auth_patch = consumed_poo_authorization_registry_patch(
                working,
                verified=verified,
                commit_id=base_result.commit_id,
            )
        except PrimeSentinelPoOAuthorizationError as exc:
            raise PoOPrimeQuorumCommitError(str(exc)) from exc
        working.update(auth_patch)

    quorum_event_id = f"SARA-EVENT-PRIME-QUORUM-{base_result.commit_id}"
    ordered = _sorted_verified(verified_assertions)
    quorum_event_patch, actual_event_id = queue_event_outbox_patch(
        working,
        event="prime_sentinel_poo_quorum_authorizations_consumed",
        actor=actor,
        event_id=quorum_event_id,
        payload={
            "commit_id": base_result.commit_id,
            "asset_id": expected["asset_id"],
            "governance_projection_digest": expected["governance_projection_digest"],
            "source_decision_digest": expected["source_decision_digest"],
            "expected_registry_digest": expected["expected_registry_digest"],
            "candidate_registry_digest": expected["candidate_registry_digest"],
            "candidate_state_digest": expected["candidate_state_digest"],
            "quorum_threshold": threshold,
            "quorum_size": len(ordered),
            "authorization_ids": [item.authorization_id for item in ordered],
            "key_ids": [item.key_id for item in ordered],
            "key_fingerprints_sha256": [
                item.key_fingerprint_sha256 for item in ordered
            ],
            "signed_assertion_sha256": [
                item.signed_assertion_sha256 for item in ordered
            ],
            "prime_quorum_cryptographic_authorization_verified": True,
            "single_signer_sufficient": False,
            "durable_internal_state_committed": True,
            "legal_title_changed": False,
            "live_value_moved": False,
            "credential_rotated": False,
            "external_transfer_executed": False,
            "claims_boundary": POO_PRIME_QUORUM_CLAIMS_BOUNDARY,
        },
    )
    if actual_event_id != quorum_event_id:
        raise PoOPrimeQuorumCommitError("PRIME quorum audit event ID changed unexpectedly")

    patch = dict(base_patch)
    patch[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY] = working[
        PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY
    ]
    patch.update(quorum_event_patch)
    return patch, _result(
        base_result,
        threshold=threshold,
        verified=verified_assertions,
    )
