from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.authorization_envelope import (
    AuthorizationDisposition,
    AuthorizationRequest,
    evaluate_authorization,
)
from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.context_lineage import ContextSourceType, evaluate_authority_claim
from worldshepherd_sara.mag1_gate import Mag1Disposition
from worldshepherd_sara.mag1_prime_binding import (
    PRIME_MAG1_ACTION,
    PRIME_MAG1_PURPOSE,
    PRIME_MAG1_SCOPE,
    PRIME_MAG1_WORKFLOW_ID,
    bind_recorded_prime_requalification,
    evaluate_prime_requalification_mag1,
)
from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    canonical_authorization_message,
    consumed_authorization_registry_patch,
    verified_authorization_registry_patch,
)
from worldshepherd_sara.trajectory_guard import (
    SideEffectClass,
    TrajectoryAction,
    TrajectoryState,
)


NOW = datetime(2026, 9, 17, 17, 30, tzinfo=timezone.utc)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keypair():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            "PS-MAG1": _b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def _assertion(
    private: Ed25519PrivateKey,
    *,
    prime_id: str = "PRIME-MAG1",
    environment: PrimeEnvironment = PrimeEnvironment.SPACE,
    authorization_id: str = "AUTH-MAG1-001",
    nonce: str = "nonce-mag1-0123456789",
) -> PrimeSentinelAuthorizationAssertion:
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-MAG1",
        authorization_id=authorization_id,
        prime_id=prime_id,
        target_environment=environment,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def _record(assertion, verifier):
    verified = verifier.verify(assertion, now=NOW)
    return verified_authorization_registry_patch({}, verified)


def _candidate() -> AutonomousActionCandidate:
    return AutonomousActionCandidate(
        action_id="C-PRIME-REQUAL",
        action_type=PRIME_MAG1_ACTION,
        confidence=1.0,
        requested_authority=1,
        reversible=True,
    )


def _policy() -> AutonomyPolicy:
    return AutonomyPolicy(
        policy_id="POL-PRIME-REQUAL",
        allowed_auto_action_types=[PRIME_MAG1_ACTION],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )


def _state() -> TrajectoryState:
    return TrajectoryState(
        trajectory_id="TRJ-PRIME-REQUAL",
        originating_human_request_hash="sha256:request",
        root_authority="PRIME_SENTINEL",
    )


def _trajectory_action() -> TrajectoryAction:
    return TrajectoryAction(
        action_id="ACT-PRIME-REQUAL",
        action_type=PRIME_MAG1_ACTION,
        side_effect=SideEffectClass.EXECUTE,
    )


def test_valid_signed_recorded_prime_authorization_derives_fixed_mag1_authority():
    private, verifier = _keypair()
    assertion = _assertion(private)
    registry = _record(assertion, verifier)
    binding = bind_recorded_prime_requalification(
        assertion=assertion,
        verifier=verifier,
        registry=registry,
        now=NOW,
    )
    envelope = binding.authorization_envelope
    assert envelope.authorization_id == "AUTH-MAG1-001"
    assert envelope.workflow_id == PRIME_MAG1_WORKFLOW_ID
    assert envelope.action == PRIME_MAG1_ACTION
    assert envelope.purpose == PRIME_MAG1_PURPOSE
    assert envelope.scopes == [PRIME_MAG1_SCOPE]
    assert envelope.resource == "prime:PRIME-MAG1:environment:SPACE"
    assert envelope.external_egress is False
    assert envelope.credential_use is False
    assert envelope.maximum_delegation_depth == 0
    assert binding.authority_artifact.source_type == ContextSourceType.PRIME_SIGNED_AUTHORIZATION
    accepted, _ = evaluate_authority_claim(binding.authority_artifact)
    assert accepted is True


def test_tampered_prime_assertion_cannot_create_mag1_binding():
    private, verifier = _keypair()
    assertion = _assertion(private)
    registry = _record(assertion, verifier)
    tampered = assertion.model_copy(update={"prime_id": "PRIME-TAMPERED"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        bind_recorded_prime_requalification(
            assertion=tampered,
            verifier=verifier,
            registry=registry,
            now=NOW,
        )


def test_registry_record_must_match_verified_signature_material():
    private, verifier = _keypair()
    assertion = _assertion(private)
    registry = _record(assertion, verifier)
    entry = dict(registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-MAG1-001"])
    entry["nonce"] = "nonce-registry-tamper-1234"
    registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-MAG1-001"] = entry
    with pytest.raises(PrimeSentinelAuthorizationError, match="nonce"):
        bind_recorded_prime_requalification(
            assertion=assertion,
            verifier=verifier,
            registry=registry,
            now=NOW,
        )


def test_derived_authority_cannot_be_repurposed_to_different_resource():
    private, verifier = _keypair()
    assertion = _assertion(private)
    binding = bind_recorded_prime_requalification(
        assertion=assertion,
        verifier=verifier,
        registry=_record(assertion, verifier),
        now=NOW,
    )
    disposition, reasons = evaluate_authorization(
        binding.authorization_envelope,
        AuthorizationRequest(
            workflow_id=PRIME_MAG1_WORKFLOW_ID,
            action=PRIME_MAG1_ACTION,
            resource="prime:PRIME-OTHER:environment:SPACE",
            purpose=PRIME_MAG1_PURPOSE,
            required_scopes=[PRIME_MAG1_SCOPE],
        ),
        now=NOW,
    )
    assert disposition == AuthorizationDisposition.DENIED
    assert any("resource" in reason for reason in reasons)


def test_consumed_prime_authorization_cannot_be_reused_by_mag1_bridge():
    private, verifier = _keypair()
    assertion = _assertion(private)
    registry = _record(assertion, verifier)
    consumed = consumed_authorization_registry_patch(
        registry,
        authorization_id="AUTH-MAG1-001",
        transition_id="PRIME-CUSTODY-001",
        consumed_at=NOW,
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="VERIFIED state"):
        bind_recorded_prime_requalification(
            assertion=assertion,
            verifier=verifier,
            registry=consumed,
            now=NOW,
        )


def test_cryptographically_bound_prime_path_passes_all_mag1_gates():
    private, verifier = _keypair()
    assertion = _assertion(private)
    decision, binding = evaluate_prime_requalification_mag1(
        assertion=assertion,
        verifier=verifier,
        registry=_record(assertion, verifier),
        candidate=_candidate(),
        autonomy_policy=_policy(),
        trajectory_state=_state(),
        trajectory_action=_trajectory_action(),
        now=NOW,
    )
    assert decision.disposition == Mag1Disposition.AUTO_ELIGIBLE
    assert decision.authorization_disposition == AuthorizationDisposition.AUTHORIZED
    assert binding.authority_artifact.source_type == ContextSourceType.PRIME_SIGNED_AUTHORIZATION
    assert decision.updated_trajectory.events[-1].action.authorization_verified is True


def test_prime_bridge_rejects_action_substitution_before_generic_mag1():
    private, verifier = _keypair()
    assertion = _assertion(private)
    candidate = _candidate().model_copy(update={"action_type": "PUBLISH_REPORT"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="only REQUALIFICATION_RELEASE"):
        evaluate_prime_requalification_mag1(
            assertion=assertion,
            verifier=verifier,
            registry=_record(assertion, verifier),
            candidate=candidate,
            autonomy_policy=_policy(),
            trajectory_state=_state(),
            trajectory_action=_trajectory_action(),
            now=NOW,
        )
