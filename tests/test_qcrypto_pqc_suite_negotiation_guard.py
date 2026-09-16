from security.qcrypto.hybrid_authority_migration import AuthorityLayer, MigrationRequirement
from security.qcrypto.pqc_suite_negotiation_guard import (
    SuiteNegotiationPolicy,
    SuiteNegotiationRequest,
    assess_suite_negotiation,
)


def policy(**overrides):
    data = dict(
        network_id="fixture-net",
        authority_layer=AuthorityLayer.ACCOUNT,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        preference_order=("PQ-MLDSA", "PQ-SLHDSA", "HYBRID-ECDSA-MLDSA"),
        policy_version=9,
    )
    data.update(overrides)
    return SuiteNegotiationPolicy(**data)


def request(**overrides):
    data = dict(
        network_id="fixture-net",
        authority_layer=AuthorityLayer.ACCOUNT,
        offered_suite_ids=("PQ-MLDSA", "HYBRID-ECDSA-MLDSA"),
        selected_suite_id="PQ-MLDSA",
        peer_capabilities_digest="a" * 64,
        policy_version=9,
    )
    data.update(overrides)
    return SuiteNegotiationRequest(**data)


def test_strongest_offered_suite_is_accepted():
    result = assess_suite_negotiation(request(), policy())
    assert result.accepted is True
    assert result.verdict == "SUITE_NEGOTIATION_ACCEPTED"
    assert result.strongest_offered_suite_id == "PQ-MLDSA"
    assert result.negotiation_transcript_digest is not None
    assert len(result.negotiation_transcript_digest) == 64
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.transaction_authorized is False


def test_weaker_selected_suite_is_rejected_when_stronger_suite_was_offered():
    result = assess_suite_negotiation(
        request(selected_suite_id="HYBRID-ECDSA-MLDSA"),
        policy(),
    )
    assert result.accepted is False
    assert result.verdict == "SUITE_DOWNGRADE_REJECTED"


def test_selected_suite_must_be_in_offer():
    result = assess_suite_negotiation(
        request(offered_suite_ids=("HYBRID-ECDSA-MLDSA",), selected_suite_id="PQ-MLDSA"),
        policy(),
    )
    assert result.accepted is False


def test_offer_with_unknown_suite_fails_closed():
    result = assess_suite_negotiation(
        request(offered_suite_ids=("PQ-MLDSA", "UNKNOWN-SUITE")),
        policy(),
    )
    assert result.accepted is False
    assert any("unrecognized" in blocker for blocker in result.blockers)


def test_duplicate_offers_fail_closed():
    result = assess_suite_negotiation(
        request(offered_suite_ids=("PQ-MLDSA", "PQ-MLDSA")),
        policy(),
    )
    assert result.accepted is False
    assert any("Duplicate" in blocker for blocker in result.blockers)


def test_policy_version_mismatch_fails_closed():
    result = assess_suite_negotiation(request(policy_version=8), policy(policy_version=9))
    assert result.accepted is False
    assert any("policy version" in blocker.lower() for blocker in result.blockers)


def test_network_and_authority_layer_are_bound():
    wrong_network = assess_suite_negotiation(request(network_id="other-net"), policy())
    assert wrong_network.accepted is False
    wrong_layer = assess_suite_negotiation(
        request(authority_layer=AuthorityLayer.CONSENSUS_VALIDATOR),
        policy(),
    )
    assert wrong_layer.accepted is False


def test_peer_capability_digest_must_be_canonical_sha256():
    result = assess_suite_negotiation(request(peer_capabilities_digest="AB" * 32), policy())
    assert result.accepted is False
    assert any("canonical lowercase SHA-256" in blocker for blocker in result.blockers)


def test_pq_minimum_rejects_hybrid_only_offer():
    result = assess_suite_negotiation(
        request(
            offered_suite_ids=("HYBRID-ECDSA-MLDSA",),
            selected_suite_id="HYBRID-ECDSA-MLDSA",
        ),
        policy(minimum_requirement=MigrationRequirement.PQ_REQUIRED),
    )
    assert result.accepted is False
    assert any("minimum migration requirement" in blocker for blocker in result.blockers)


def test_offer_order_is_transcript_bound():
    a = assess_suite_negotiation(request(), policy())
    b = assess_suite_negotiation(
        request(offered_suite_ids=("HYBRID-ECDSA-MLDSA", "PQ-MLDSA")),
        policy(),
    )
    assert a.accepted is True
    assert b.accepted is True
    assert a.negotiation_transcript_digest != b.negotiation_transcript_digest
