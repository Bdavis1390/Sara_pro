from dataclasses import replace

from security.qcrypto.canonical_pq_context_interop import CanonicalPQInteropResult
from security.qcrypto.canonical_pq_signing_context import CanonicalSigningContextDecision
from security.qcrypto.canonical_replay_freshness_guard import (
    ReplayCheckpoint,
    ReplayFreshnessDecision,
)
from security.qcrypto.governed_pq_signing_state_machine import (
    GovernedSigningState,
    assess_governed_signing_readiness,
)
from security.qcrypto.negotiated_canonical_context import NegotiatedCanonicalContextDecision


CANONICAL = "a" * 64
NEGOTIATED = "b" * 64
TRANSCRIPT = "c" * 64


def canonical(**overrides):
    data = dict(
        verdict="CANONICAL_SIGNING_CONTEXT_READY",
        ready=True,
        blockers=(),
        context_schema="WS-QCRYPTO-CANONICAL-SIGNING-CONTEXT-V1",
        context_digest=CANONICAL,
        canonical_preimage_hex="00",
        canonical_fields={
            "network_id": "fixture-net",
            "authority_id": "fixture-authority",
            "replay_domain": "tx-auth",
            "pq_algorithm_id": "ML-DSA",
        },
        pre_sign_intent_only=True,
        signature_presence_assumed=False,
    )
    data.update(overrides)
    return CanonicalSigningContextDecision(**data)


def negotiated(**overrides):
    data = dict(
        verdict="NEGOTIATED_CANONICAL_CONTEXT_READY",
        ready=True,
        blockers=(),
        canonical_context_digest=CANONICAL,
        negotiation_transcript_digest=TRANSCRIPT,
        negotiated_context_digest=NEGOTIATED,
        selected_suite_id="HYBRID-ECDSA-MLDSA",
        effective_requirement="HYBRID_REQUIRED",
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        pre_sign_intent_only=True,
        signature_presence_assumed=False,
    )
    data.update(overrides)
    return NegotiatedCanonicalContextDecision(**data)


def checkpoint(**overrides):
    data = dict(
        network_id="fixture-net",
        authority_id="fixture-authority",
        replay_domain="tx-auth",
        highest_replay_sequence=1,
        highest_key_epoch=1,
        highest_policy_version=1,
        highest_envelope_version=1,
        last_context_digest=CANONICAL,
    )
    data.update(overrides)
    return ReplayCheckpoint(**data)


def replay(**overrides):
    data = dict(
        verdict="REPLAY_FRESHNESS_ACCEPTED",
        accepted=True,
        blockers=(),
        warnings=(),
        next_checkpoint=checkpoint(),
        duplicate_context=False,
        replay_sequence_advanced=True,
    )
    data.update(overrides)
    return ReplayFreshnessDecision(**data)


def probe(scheme="ML-DSA-65", **overrides):
    data = dict(
        scheme=scheme,
        backend_module="pqcrypto.sign.fixture",
        canonical_context_digest=NEGOTIATED,
        public_key_bytes=1,
        signature_bytes=1,
        public_key_fingerprint="d" * 64,
        valid_signature_verified=True,
        tampered_context_rejected=True,
        cross_context_replay_rejected=True,
        wrong_key_rejected=True,
        test_signature_generated=True,
        secret_material_retained=False,
    )
    data.update(overrides)
    return CanonicalPQInteropResult(**data)


def test_complete_bounded_evidence_chain_stops_at_human_review():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(),
        (probe("ML-DSA-65"), probe("ML-DSA-87"), probe("SLH-DSA-SHA2-128s")),
    )
    assert result.verdict == "GOVERNED_PQ_SIGNING_READY_FOR_HUMAN_REVIEW"
    assert result.state == GovernedSigningState.HUMAN_REVIEW_REQUIRED.value
    assert result.ready_for_human_review is True
    assert result.compatible_probe_count == 2
    assert result.verified_compatible_probe_count == 2
    assert result.replay_checkpoint_bound is True
    assert result.human_approval_required is True
    assert result.human_approval_recorded is False
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.live_transaction_signed is False
    assert result.production_protocol_integration is False
    assert result.end_to_end_pq_security_established is False
    assert any("outside the negotiated PQ algorithm family" in warning for warning in result.warnings)


def test_unready_canonical_context_blocks_entire_chain():
    result = assess_governed_signing_readiness(
        canonical(ready=False, context_digest=None), negotiated(), replay(), (probe(),)
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.ready_for_human_review is False
    assert any("Canonical pre-sign context is not ready" in blocker for blocker in result.blockers)


def test_negotiated_context_must_bind_same_canonical_digest():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(canonical_context_digest="e" * 64),
        replay(),
        (probe(),),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert any("not bound to the supplied canonical context" in blocker for blocker in result.blockers)


def test_replay_checkpoint_must_bind_canonical_digest():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(next_checkpoint=checkpoint(last_context_digest="e" * 64)),
        (probe(),),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.replay_checkpoint_bound is False
    assert any("Replay checkpoint is not bound" in blocker for blocker in result.blockers)


def test_replay_rejection_blocks_before_signature_readiness():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(verdict="REPLAY_DUPLICATE_REJECTED", accepted=False, next_checkpoint=None),
        (probe(),),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.verified_compatible_probe_count == 0
    assert any("Replay/freshness gate did not accept" in blocker for blocker in result.blockers)


def test_incompatible_pq_family_cannot_satisfy_negotiated_mldsa_suite():
    result = assess_governed_signing_readiness(
        canonical(), negotiated(), replay(), (probe("SLH-DSA-SHA2-128s"),)
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.compatible_probe_count == 0
    assert any("No PQ reference-signature probe is compatible" in blocker for blocker in result.blockers)


def test_compatible_probe_must_bind_negotiated_digest():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(),
        (probe(canonical_context_digest="e" * 64),),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert any("not bound to the negotiated context digest" in blocker for blocker in result.blockers)


def test_any_failed_compatible_probe_fails_closed():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(),
        (probe("ML-DSA-65"), probe("ML-DSA-87", wrong_key_rejected=False)),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.compatible_probe_count == 2
    assert result.verified_compatible_probe_count == 1
    assert any("did not satisfy fail-closed test controls" in blocker for blocker in result.blockers)


def test_probe_cannot_carry_live_value_or_execution_authority():
    result = assess_governed_signing_readiness(
        canonical(),
        negotiated(),
        replay(),
        (probe(live_value_authorized=True, execution_authority=True),),
    )
    assert result.state == GovernedSigningState.BLOCKED.value
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.human_approval_recorded is False
