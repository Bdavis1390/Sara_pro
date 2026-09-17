from dataclasses import replace

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_signing_context import (
    AuthoritySigningIntent,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.hybrid_authority_migration import (
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)
from security.qcrypto.negotiated_canonical_context import bind_negotiated_canonical_context
from security.qcrypto.pqc_suite_negotiation_guard import (
    SuiteNegotiationPolicy,
    SuiteNegotiationRequest,
)


NETWORK = "negotiation-testnet"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def canonical_context(*, classical="ECDSA", pq="ML-DSA", policy_version=12):
    intent = AuthoritySigningIntent(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest="a" * 64,
        authority_id="authority-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=2,
        key_epoch=9,
        classical_algorithm_id=classical,
        pq_algorithm_id=pq,
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    authority_policy = AuthorityPolicy(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=2,
        minimum_key_epoch=9,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
        chain="NegotiationChain",
        adapter_class="PROGRAMMABLE_AUTH",
        stable_authority_id=True,
        authenticator_versioned=True,
        authenticator_replaceable=True,
        policy_versioned=True,
        recovery_commitment_present=True,
        chain_binding_present=True,
        replay_domain_present=True,
        evidence_binding_present=True,
        explicit_human_approval_required=True,
        live_chain_support=False,
        independent_review_complete=False,
        consensus_layer_pq=False,
    )
    result = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent,
            authority_policy=authority_policy,
            adapter=adapter,
            policy_version=policy_version,
            replay_domain="negotiated-auth",
            replay_sequence=1,
            evidence_digest="b" * 64,
            recovery_commitment_digest="c" * 64,
        )
    )
    assert result.ready is True
    assert result.pre_sign_intent_only is True
    assert result.signature_presence_assumed is False
    return result


def negotiation_request(**overrides):
    data = dict(
        network_id=NETWORK,
        authority_layer=AuthorityLayer.ACCOUNT,
        offered_suite_ids=("HYBRID-ECDSA-MLDSA",),
        selected_suite_id="HYBRID-ECDSA-MLDSA",
        peer_capabilities_digest="d" * 64,
        policy_version=12,
    )
    data.update(overrides)
    return SuiteNegotiationRequest(**data)


def negotiation_policy(**overrides):
    data = dict(
        network_id=NETWORK,
        authority_layer=AuthorityLayer.ACCOUNT,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        preference_order=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA", "HYBRID-ED25519-MLDSA"),
        policy_version=12,
    )
    data.update(overrides)
    return SuiteNegotiationPolicy(**data)


def test_accepted_suite_transcript_binds_to_canonical_pre_sign_context():
    result = bind_negotiated_canonical_context(
        canonical_context(), negotiation_request(), negotiation_policy()
    )
    assert result.ready is True
    assert result.verdict == "NEGOTIATED_CANONICAL_CONTEXT_READY"
    assert result.selected_suite_id == "HYBRID-ECDSA-MLDSA"
    assert result.effective_requirement == "HYBRID_REQUIRED"
    assert result.classical_algorithm_id == "ECDSA"
    assert result.pq_algorithm_id == "ML-DSA"
    assert result.negotiation_transcript_digest is not None
    assert result.negotiated_context_digest is not None
    assert len(result.negotiated_context_digest) == 64
    assert result.pre_sign_intent_only is True
    assert result.signature_presence_assumed is False
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.transaction_signed is False


def test_capability_transcript_change_changes_negotiated_context_digest():
    base = bind_negotiated_canonical_context(
        canonical_context(), negotiation_request(peer_capabilities_digest="d" * 64), negotiation_policy()
    )
    changed = bind_negotiated_canonical_context(
        canonical_context(), negotiation_request(peer_capabilities_digest="e" * 64), negotiation_policy()
    )
    assert base.ready and changed.ready
    assert base.negotiation_transcript_digest != changed.negotiation_transcript_digest
    assert base.negotiated_context_digest != changed.negotiated_context_digest


def test_weaker_selected_suite_is_rejected_when_stronger_suite_was_offered():
    request = negotiation_request(
        offered_suite_ids=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
        selected_suite_id="HYBRID-ECDSA-MLDSA",
    )
    result = bind_negotiated_canonical_context(canonical_context(), request, negotiation_policy())
    assert result.ready is False
    assert any("downgrade" in blocker.lower() for blocker in result.blockers)
    assert result.negotiated_context_digest is None


def test_negotiated_algorithm_must_match_canonical_algorithm_slots():
    request = negotiation_request(
        offered_suite_ids=("HYBRID-ED25519-MLDSA",),
        selected_suite_id="HYBRID-ED25519-MLDSA",
    )
    result = bind_negotiated_canonical_context(canonical_context(), request, negotiation_policy())
    assert result.ready is False
    assert any("classical algorithm" in blocker.lower() for blocker in result.blockers)


def test_negotiation_policy_floor_must_match_canonical_policy_floor():
    result = bind_negotiated_canonical_context(
        canonical_context(),
        negotiation_request(),
        negotiation_policy(minimum_requirement=MigrationRequirement.CLASSICAL_ALLOWED),
    )
    assert result.ready is False
    assert any("minimum requirement" in blocker.lower() for blocker in result.blockers)


def test_network_and_policy_version_mismatch_fail_closed():
    network_mismatch = bind_negotiated_canonical_context(
        canonical_context(),
        negotiation_request(network_id="other-network"),
        negotiation_policy(network_id="other-network"),
    )
    assert network_mismatch.ready is False
    assert any("network id" in blocker.lower() for blocker in network_mismatch.blockers)

    version_mismatch = bind_negotiated_canonical_context(
        canonical_context(),
        negotiation_request(policy_version=13),
        negotiation_policy(policy_version=13),
    )
    assert version_mismatch.ready is False
    assert any("policy version" in blocker.lower() for blocker in version_mismatch.blockers)


def test_unready_canonical_context_never_enters_negotiated_ready_state():
    ready = canonical_context()
    blocked_context = replace(ready, ready=False, context_digest=None)
    result = bind_negotiated_canonical_context(
        blocked_context, negotiation_request(), negotiation_policy()
    )
    assert result.ready is False
    assert result.negotiated_context_digest is None
