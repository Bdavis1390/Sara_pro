from dataclasses import replace

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_signing_context import (
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.hybrid_authority_migration import (
    AuthorityEnvelope,
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)


PAYLOAD = "a" * 64
EVIDENCE = "b" * 64
RECOVERY = "c" * 64
NETWORK = "testnet-fixture"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def authority(**overrides):
    data = dict(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest=PAYLOAD,
        authority_id="authority-fixture-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=3,
        key_epoch=11,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_signature_present=True,
        pq_signature_present=True,
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
        execution_authority=False,
        live_value_authorized=False,
    )
    data.update(overrides)
    return AuthorityEnvelope(**data)


def policy(**overrides):
    data = dict(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=3,
        minimum_key_epoch=11,
        require_recovery_evidence=True,
    )
    data.update(overrides)
    return AuthorityPolicy(**data)


def adapter(**overrides):
    data = dict(
        chain="FixtureChain",
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
    data.update(overrides)
    return CanonicalAuthorityEnvelope(**data)


def request(**overrides):
    data = dict(
        authority=authority(),
        authority_policy=policy(),
        adapter=adapter(),
        policy_version=5,
        replay_domain="tx-auth",
        replay_sequence=42,
        evidence_digest=EVIDENCE,
        recovery_commitment_digest=RECOVERY,
    )
    data.update(overrides)
    return CanonicalSigningContextRequest(**data)


def ready_digest(req=None):
    result = build_canonical_signing_context(req or request())
    assert result.ready is True
    assert result.verdict == "CANONICAL_SIGNING_CONTEXT_READY"
    assert result.context_digest is not None
    assert len(result.context_digest) == 64
    assert result.canonical_preimage_hex is not None
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.transaction_signed is False
    return result.context_digest


def test_context_is_deterministic_for_identical_inputs():
    assert ready_digest() == ready_digest()


def test_network_binding_changes_context_digest():
    base = ready_digest()
    alt_authority = replace(authority(), network_id="other-testnet")
    alt_policy = replace(policy(), network_id="other-testnet")
    changed = ready_digest(request(authority=alt_authority, authority_policy=alt_policy))
    assert changed != base


def test_authority_role_binding_changes_context_digest():
    base = ready_digest()
    changed = ready_digest(
        request(authority=replace(authority(), authority_layer=AuthorityLayer.CONSENSUS_VALIDATOR))
    )
    assert changed != base


def test_algorithm_suite_binding_changes_context_digest():
    base = ready_digest()
    changed = ready_digest(request(authority=replace(authority(), pq_algorithm_id="SLH-DSA")))
    assert changed != base


def test_policy_version_binding_changes_context_digest():
    assert ready_digest(request(policy_version=5)) != ready_digest(request(policy_version=6))


def test_key_epoch_binding_changes_context_digest_when_policy_allows_new_epoch():
    base = ready_digest()
    changed = ready_digest(request(authority=replace(authority(), key_epoch=12)))
    assert changed != base


def test_replay_sequence_binding_changes_context_digest():
    assert ready_digest(request(replay_sequence=42)) != ready_digest(request(replay_sequence=43))


def test_payload_evidence_and_recovery_are_independently_bound():
    base = ready_digest()
    assert ready_digest(request(authority=replace(authority(), payload_digest="d" * 64))) != base
    assert ready_digest(request(evidence_digest="e" * 64)) != base
    assert ready_digest(request(recovery_commitment_digest="f" * 64)) != base


def test_policy_downgrade_blocks_context_generation():
    downgraded = replace(authority(), declared_requirement=MigrationRequirement.CLASSICAL_ALLOWED)
    result = build_canonical_signing_context(request(authority=downgraded))
    assert result.ready is False
    assert result.context_digest is None
    assert any("downgrade" in blocker.lower() for blocker in result.blockers)


def test_self_asserted_execution_authority_blocks_context_generation():
    result = build_canonical_signing_context(
        request(authority=replace(authority(), execution_authority=True))
    )
    assert result.ready is False
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.transaction_signed is False


def test_missing_adapter_replay_binding_fails_closed():
    result = build_canonical_signing_context(request(adapter=adapter(replay_domain_present=False)))
    assert result.ready is False
    assert any("replay-domain" in blocker for blocker in result.blockers)


def test_noncanonical_uppercase_digest_fails_closed():
    result = build_canonical_signing_context(request(evidence_digest="AB" * 32))
    assert result.ready is False
    assert any("lowercase" in blocker for blocker in result.blockers)


def test_missing_recovery_commitment_digest_fails_closed():
    result = build_canonical_signing_context(request(recovery_commitment_digest=None))
    assert result.ready is False
    assert any("recovery_commitment_digest is required" in blocker for blocker in result.blockers)


def test_unsupported_identifier_characters_fail_closed():
    result = build_canonical_signing_context(request(replay_domain="tx auth"))
    assert result.ready is False
    assert any("unsupported characters" in blocker for blocker in result.blockers)
