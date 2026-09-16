from dataclasses import replace

import pytest

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_context_interop import (
    run_all_canonical_context_probes,
    run_canonical_context_probe,
)
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
from security.qcrypto.pq_signature_interop import SCHEMES


PAYLOAD = "a" * 64
EVIDENCE = "b" * 64
RECOVERY = "c" * 64


def intent(**overrides):
    data = dict(
        network_id="interop-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        payload_digest=PAYLOAD,
        authority_id="interop-authority-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=5,
        key_epoch=30,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    data.update(overrides)
    return AuthoritySigningIntent(**data)


def policy(**overrides):
    data = dict(
        network_id="interop-testnet",
        domain_separator="WS-QCRYPTO-AUTH-V1",
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=5,
        minimum_key_epoch=30,
        require_recovery_evidence=True,
    )
    data.update(overrides)
    return AuthorityPolicy(**data)


def adapter():
    return CanonicalAuthorityEnvelope(
        chain="InteropChain",
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


def context(replay_sequence=500):
    result = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent(),
            authority_policy=policy(),
            adapter=adapter(),
            policy_version=9,
            replay_domain="canonical-authority",
            replay_sequence=replay_sequence,
            evidence_digest=EVIDENCE,
            recovery_commitment_digest=RECOVERY,
        )
    )
    if result.ready:
        assert result.pre_sign_intent_only is True
        assert result.signature_presence_assumed is False
    return result


def test_all_standardized_pq_schemes_sign_after_intent_commitment_and_reject_replay():
    primary = context(500)
    alternate = context(501)
    results = run_all_canonical_context_probes(primary, alternate)
    assert len(results) == len(SCHEMES) == 3
    for result in results:
        assert result.valid_signature_verified is True
        assert result.tampered_context_rejected is True
        assert result.cross_context_replay_rejected is True
        assert result.wrong_key_rejected is True
        assert result.test_signature_generated is True
        assert result.secret_material_retained is False
        assert result.live_transaction_signed is False
        assert result.live_value_authorized is False
        assert result.execution_authority is False


def test_each_scheme_is_bound_to_exact_pre_sign_context_commitment():
    primary = context(500)
    alternate = context(501)
    for scheme in SCHEMES:
        result = run_canonical_context_probe(scheme, primary, alternate)
        assert result.scheme == scheme
        assert result.canonical_context_digest == primary.context_digest
        assert result.cross_context_replay_rejected is True


def test_unready_intent_context_cannot_enter_signature_interop():
    blocked = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=replace(intent(), declared_requirement=MigrationRequirement.CLASSICAL_ALLOWED),
            authority_policy=policy(),
            adapter=adapter(),
            policy_version=9,
            replay_domain="canonical-authority",
            replay_sequence=500,
            evidence_digest=EVIDENCE,
            recovery_commitment_digest=RECOVERY,
        )
    )
    assert blocked.ready is False
    with pytest.raises(ValueError, match="must be ready"):
        run_canonical_context_probe("ML-DSA-65", blocked, context(501))


def test_identical_context_cannot_be_used_as_replay_negative_control():
    primary = context(500)
    with pytest.raises(ValueError, match="distinct commitment"):
        run_canonical_context_probe("ML-DSA-65", primary, primary)
