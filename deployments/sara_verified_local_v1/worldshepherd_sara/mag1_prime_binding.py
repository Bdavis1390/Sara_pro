from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict

from .authorization_envelope import AuthorizationEnvelope, AuthorizationRequest
from .autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from .context_lineage import ContextArtifact, ContextSourceType
from .mag1_gate import Mag1Decision, evaluate_mag1
from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    VerifiedPrimeSentinelAuthorization,
    assert_recorded_authorization_usable,
    canonical_authorization_message,
)
from .trajectory_guard import TrajectoryAction, TrajectoryGuardPolicy, TrajectoryState


PRIME_MAG1_WORKFLOW_ID = "PRIME_REQUALIFICATION_RELEASE"
PRIME_MAG1_ACTION = "REQUALIFICATION_RELEASE"
PRIME_MAG1_PURPOSE = "governed PRIME requalification release"
PRIME_MAG1_SCOPE = "prime:requalification_release"


class PrimeMag1Binding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: VerifiedPrimeSentinelAuthorization
    authorization_envelope: AuthorizationEnvelope
    authority_artifact: ContextArtifact


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise PrimeSentinelAuthorizationError("recorded authorization timestamp is not timezone-aware")
    return value.astimezone(timezone.utc)


def _recorded_datetime(entry: dict[str, Any], key: str) -> datetime:
    try:
        value = datetime.fromisoformat(str(entry[key]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise PrimeSentinelAuthorizationError(
            f"recorded authorization {key} is invalid"
        ) from exc
    return _utc(value)


def _resource(verified: VerifiedPrimeSentinelAuthorization) -> str:
    return (
        f"prime:{verified.prime_id}:environment:"
        f"{verified.target_environment.value}"
    )


def bind_recorded_prime_requalification(
    *,
    assertion: PrimeSentinelAuthorizationAssertion,
    verifier: PrimeSentinelVerifier,
    registry: dict[str, Any],
    now: datetime | None = None,
) -> PrimeMag1Binding:
    """Derive MAG-1 authority only from a valid, recorded PRIME assertion.

    The bridge is deliberately narrow: it cannot bless caller-selected actions,
    purposes, scopes, resources, destinations, egress, credential use, or
    delegation. Every generic MAG-1 field is derived from signed PRIME fields or
    fixed constants owned by this bridge.
    """

    current = now or datetime.now(timezone.utc)
    verified = verifier.verify(assertion, now=current)
    entry = assert_recorded_authorization_usable(
        registry,
        authorization_id=verified.authorization_id,
        prime_id=verified.prime_id,
        target_environment=verified.target_environment,
        verifier=verifier,
        now=current,
    )

    expected = {
        "key_id": verified.key_id,
        "key_fingerprint_sha256": verified.key_fingerprint_sha256,
        "nonce": verified.nonce,
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            raise PrimeSentinelAuthorizationError(
                f"recorded authorization {key} does not match verified assertion"
            )
    if _recorded_datetime(entry, "issued_at") != _utc(verified.issued_at):
        raise PrimeSentinelAuthorizationError(
            "recorded authorization issued_at does not match verified assertion"
        )
    if _recorded_datetime(entry, "expires_at") != _utc(verified.expires_at):
        raise PrimeSentinelAuthorizationError(
            "recorded authorization expires_at does not match verified assertion"
        )

    signed_material = (
        canonical_authorization_message(assertion)
        + b"."
        + assertion.signature_b64url.encode("ascii")
    )
    authority_hash = "sha256:" + hashlib.sha256(signed_material).hexdigest()
    resource = _resource(verified)

    envelope = AuthorizationEnvelope(
        authorization_id=verified.authorization_id,
        principal=f"PRIME_SENTINEL:{verified.key_id}",
        workflow_id=PRIME_MAG1_WORKFLOW_ID,
        action=PRIME_MAG1_ACTION,
        resource=resource,
        purpose=PRIME_MAG1_PURPOSE,
        scopes=[PRIME_MAG1_SCOPE],
        destinations=[],
        issued_at=verified.issued_at,
        expires_at=verified.expires_at,
        maximum_delegation_depth=0,
        delegation_depth=0,
        external_egress=False,
        credential_use=False,
    )
    authority_artifact = ContextArtifact(
        artifact_id=f"PRIME-AUTHZ-{verified.authorization_id}",
        source_type=ContextSourceType.PRIME_SIGNED_AUTHORIZATION,
        source_ref=(
            f"prime-sentinel:{verified.key_id}:authorization:"
            f"{verified.authorization_id}"
        ),
        content_hash=authority_hash,
    )
    return PrimeMag1Binding(
        verified=verified,
        authorization_envelope=envelope,
        authority_artifact=authority_artifact,
    )


def evaluate_prime_requalification_mag1(
    *,
    assertion: PrimeSentinelAuthorizationAssertion,
    verifier: PrimeSentinelVerifier,
    registry: dict[str, Any],
    candidate: AutonomousActionCandidate,
    autonomy_policy: AutonomyPolicy,
    trajectory_state: TrajectoryState,
    trajectory_action: TrajectoryAction,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
    now: datetime | None = None,
) -> tuple[Mag1Decision, PrimeMag1Binding]:
    """Run the cryptographically bound MAG-1 path for PRIME requalification.

    This evaluates eligibility only. The actual requalification transition must
    still consume the one-time PRIME authorization through the existing PRIME
    custody path; MAG-1 does not silently consume authority during evaluation.
    """

    if candidate.action_type != PRIME_MAG1_ACTION:
        raise PrimeSentinelAuthorizationError(
            "MAG-1 PRIME bridge accepts only REQUALIFICATION_RELEASE candidates"
        )
    if trajectory_action.action_type != PRIME_MAG1_ACTION:
        raise PrimeSentinelAuthorizationError(
            "MAG-1 PRIME bridge accepts only REQUALIFICATION_RELEASE trajectory actions"
        )

    binding = bind_recorded_prime_requalification(
        assertion=assertion,
        verifier=verifier,
        registry=registry,
        now=now,
    )
    request = AuthorizationRequest(
        workflow_id=PRIME_MAG1_WORKFLOW_ID,
        action=PRIME_MAG1_ACTION,
        resource=binding.authorization_envelope.resource,
        purpose=PRIME_MAG1_PURPOSE,
        required_scopes=[PRIME_MAG1_SCOPE],
        destination=None,
        external_egress=False,
        credential_use=False,
        requested_delegation_depth=0,
    )
    decision = evaluate_mag1(
        candidate=candidate,
        autonomy_policy=autonomy_policy,
        trajectory_state=trajectory_state,
        trajectory_action=trajectory_action,
        trajectory_policy=trajectory_policy,
        authorization_required=True,
        authorization_envelope=binding.authorization_envelope,
        authorization_request=request,
        authority_artifact=binding.authority_artifact,
        authorization_now=now,
    )
    return decision, binding
