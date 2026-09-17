from dataclasses import replace

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_signing_context import (
    AuthoritySigningIntent,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.canonical_replay_freshness_guard import (
    ReplayCandidate,
    ReplayFreshnessPolicy,
    assess_replay_freshness,
)
from security.qcrypto.hybrid_authority_migration import (
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)


NETWORK = "replay-fixture"
DOMAIN = "WS-QCRYPTO-AUTH-V1"


def canonical_context(*, sequence=1, key_epoch=4, policy_version=7, envelope_version=3, replay_domain="tx-auth"):
    intent = AuthoritySigningIntent(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        payload_digest="a" * 64,
        authority_id="authority-1",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=envelope_version,
        key_epoch=key_epoch,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id="ML-DSA",
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    authority_policy = AuthorityPolicy(
        network_id=NETWORK,
        domain_separator=DOMAIN,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=1,
        minimum_key_epoch=0,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
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
    result = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            intent=intent,
            authority_policy=authority_policy,
            adapter=adapter,
            policy_version=policy_version,
            replay_domain=replay_domain,
            replay_sequence=sequence,
            evidence_digest="b" * 64,
            recovery_commitment_digest="c" * 64,
        )
    )
    assert result.ready is True
    return result


def candidate(context=None, *, valid_from=1_000, valid_until=1_600, observed=1_200):
    return ReplayCandidate(
        context=context or canonical_context(),
        valid_from_epoch_seconds=valid_from,
        valid_until_epoch_seconds=valid_until,
        observed_at_epoch_seconds=observed,
    )


def test_first_fresh_context_creates_checkpoint_without_execution_authority():
    result = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    assert result.accepted is True
    assert result.verdict == "REPLAY_FRESHNESS_ACCEPTED"
    assert result.next_checkpoint is not None
    assert result.next_checkpoint.highest_replay_sequence == 1
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.transaction_authorized is False


def test_duplicate_context_digest_is_rejected():
    first = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    duplicate = assess_replay_freshness(candidate(), ReplayFreshnessPolicy(), first.next_checkpoint)
    assert duplicate.accepted is False
    assert duplicate.verdict == "REPLAY_DUPLICATE_REJECTED"
    assert duplicate.duplicate_context is True


def test_next_sequence_advances_checkpoint():
    first = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    second_context = canonical_context(sequence=2)
    second = assess_replay_freshness(candidate(second_context), ReplayFreshnessPolicy(), first.next_checkpoint)
    assert second.accepted is True
    assert second.next_checkpoint is not None
    assert second.next_checkpoint.highest_replay_sequence == 2
    assert second.replay_sequence_advanced is True


def test_skipped_sequence_rejected_in_strict_mode():
    first = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    skipped = assess_replay_freshness(
        candidate(canonical_context(sequence=3)),
        ReplayFreshnessPolicy(require_strict_sequence_increment=True),
        first.next_checkpoint,
    )
    assert skipped.accepted is False
    assert skipped.verdict == "REPLAY_SEQUENCE_REJECTED"


def test_non_strict_mode_allows_forward_gap_but_never_replay():
    first = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    jumped = assess_replay_freshness(
        candidate(canonical_context(sequence=3)),
        ReplayFreshnessPolicy(require_strict_sequence_increment=False),
        first.next_checkpoint,
    )
    assert jumped.accepted is True
    replayed = assess_replay_freshness(
        candidate(canonical_context(sequence=2)),
        ReplayFreshnessPolicy(require_strict_sequence_increment=False),
        jumped.next_checkpoint,
    )
    assert replayed.accepted is False
    assert replayed.verdict == "REPLAY_SEQUENCE_REJECTED"


def test_expired_context_rejected():
    result = assess_replay_freshness(
        candidate(valid_from=1_000, valid_until=1_100, observed=1_200),
        ReplayFreshnessPolicy(maximum_clock_skew_seconds=0),
    )
    assert result.accepted is False
    assert result.verdict == "FRESHNESS_REJECTED"


def test_not_yet_valid_context_rejected():
    result = assess_replay_freshness(
        candidate(valid_from=1_100, valid_until=1_500, observed=1_000),
        ReplayFreshnessPolicy(maximum_clock_skew_seconds=0),
    )
    assert result.accepted is False
    assert result.verdict == "FRESHNESS_REJECTED"


def test_oversized_validity_window_rejected():
    result = assess_replay_freshness(
        candidate(valid_from=1_000, valid_until=5_001, observed=1_200),
        ReplayFreshnessPolicy(maximum_validity_seconds=3_600),
    )
    assert result.accepted is False
    assert any("maximum duration" in blocker for blocker in result.blockers)


def test_key_epoch_rollback_rejected_even_with_new_sequence():
    first = assess_replay_freshness(candidate(canonical_context(key_epoch=5)), ReplayFreshnessPolicy())
    rollback = assess_replay_freshness(
        candidate(canonical_context(sequence=2, key_epoch=4)),
        ReplayFreshnessPolicy(),
        first.next_checkpoint,
    )
    assert rollback.accepted is False
    assert rollback.verdict == "MONOTONIC_STATE_ROLLBACK_REJECTED"


def test_policy_version_rollback_rejected_even_with_new_sequence():
    first = assess_replay_freshness(candidate(canonical_context(policy_version=8)), ReplayFreshnessPolicy())
    rollback = assess_replay_freshness(
        candidate(canonical_context(sequence=2, policy_version=7)),
        ReplayFreshnessPolicy(),
        first.next_checkpoint,
    )
    assert rollback.accepted is False
    assert rollback.verdict == "MONOTONIC_STATE_ROLLBACK_REJECTED"


def test_envelope_version_rollback_rejected_even_with_new_sequence():
    first = assess_replay_freshness(candidate(canonical_context(envelope_version=4)), ReplayFreshnessPolicy())
    rollback = assess_replay_freshness(
        candidate(canonical_context(sequence=2, envelope_version=3)),
        ReplayFreshnessPolicy(),
        first.next_checkpoint,
    )
    assert rollback.accepted is False
    assert rollback.verdict == "MONOTONIC_STATE_ROLLBACK_REJECTED"


def test_replay_domain_change_cannot_reuse_checkpoint():
    first = assess_replay_freshness(candidate(), ReplayFreshnessPolicy())
    changed = assess_replay_freshness(
        candidate(canonical_context(sequence=2, replay_domain="validator-auth")),
        ReplayFreshnessPolicy(),
        first.next_checkpoint,
    )
    assert changed.accepted is False
    assert any("replay domain" in blocker for blocker in changed.blockers)


def test_unready_context_fails_closed():
    ready = canonical_context()
    blocked = replace(ready, ready=False, context_digest=None, canonical_fields={})
    result = assess_replay_freshness(candidate(blocked), ReplayFreshnessPolicy())
    assert result.accepted is False
    assert result.next_checkpoint is None
