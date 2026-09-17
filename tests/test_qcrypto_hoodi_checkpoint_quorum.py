from security.qcrypto.hoodi_checkpoint_quorum import (
    HOODI_CHECKPOINT_PROVIDERS,
    assess_hoodi_checkpoint_quorum,
)


ROOT_A = "0x" + "a" * 64
ROOT_B = "0x" + "b" * 64


def test_two_of_three_agreement_accepts_configured_provider_in_quorum():
    result = assess_hoodi_checkpoint_quorum(
        HOODI_CHECKPOINT_PROVIDERS["sigma_prime"],
        {
            "sigma_prime": ROOT_A,
            "ethpandaops": ROOT_A,
            "ethstaker": ROOT_B,
        },
    )
    assert result.state == "HOODI_CHECKPOINT_QUORUM_ACCEPTED"
    assert result.accepted is True
    assert result.quorum_root == ROOT_A
    assert result.quorum_count == 2
    assert set(result.agreeing_providers) == {"sigma_prime", "ethpandaops"}
    assert result.consensus_verification_replaced is False


def test_configured_provider_outside_majority_fails_closed():
    result = assess_hoodi_checkpoint_quorum(
        HOODI_CHECKPOINT_PROVIDERS["sigma_prime"],
        {
            "sigma_prime": ROOT_B,
            "ethpandaops": ROOT_A,
            "ethstaker": ROOT_A,
        },
    )
    assert result.state == "HOODI_CHECKPOINT_QUORUM_REJECTED"
    assert result.accepted is False
    assert any("disagrees" in blocker for blocker in result.blockers)


def test_unreviewed_provider_url_fails_closed():
    result = assess_hoodi_checkpoint_quorum(
        "https://example.invalid/hoodi",
        {"sigma_prime": ROOT_A, "ethpandaops": ROOT_A},
    )
    assert result.accepted is False
    assert any("reviewed provider set" in blocker for blocker in result.blockers)


def test_single_provider_is_not_quorum():
    result = assess_hoodi_checkpoint_quorum(
        HOODI_CHECKPOINT_PROVIDERS["sigma_prime"],
        {"sigma_prime": ROOT_A},
    )
    assert result.accepted is False
    assert result.quorum_count == 1


def test_three_way_disagreement_is_rejected():
    result = assess_hoodi_checkpoint_quorum(
        HOODI_CHECKPOINT_PROVIDERS["sigma_prime"],
        {
            "sigma_prime": ROOT_A,
            "ethpandaops": ROOT_B,
            "ethstaker": "0x" + "c" * 64,
        },
    )
    assert result.accepted is False
    assert result.quorum_count == 1


def test_malformed_root_is_rejected():
    result = assess_hoodi_checkpoint_quorum(
        HOODI_CHECKPOINT_PROVIDERS["sigma_prime"],
        {"sigma_prime": ROOT_A, "ethpandaops": "not-a-root"},
    )
    assert result.accepted is False
    assert any("Invalid finalized root" in blocker for blocker in result.blockers)
