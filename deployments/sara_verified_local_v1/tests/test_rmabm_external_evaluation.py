from __future__ import annotations

import copy

import pytest

from worldshepherd_sara.rmabm import ALLOWED_ACTION
from worldshepherd_sara.rmabm_external_evaluation import (
    build_external_evaluation_attestation,
    build_external_evaluation_challenge,
    execute_external_evaluation_challenge,
)


def test_same_evaluator_seed_produces_same_challenge_and_result():
    first = build_external_evaluation_challenge(
        challenge_id="g4-independent-reproduction-001",
        evaluator_seed=9675,
    )
    second = build_external_evaluation_challenge(
        challenge_id="g4-independent-reproduction-001",
        evaluator_seed=9675,
    )

    assert first == second
    first_result = execute_external_evaluation_challenge(first)
    second_result = execute_external_evaluation_challenge(second)
    assert first_result == second_result
    assert first_result.audit_sha256 == second_result.audit_sha256
    assert first_result.metrics.deterministic_replay_digest == second_result.metrics.deterministic_replay_digest


def test_different_evaluator_seed_changes_challenge_digest():
    first = build_external_evaluation_challenge(
        challenge_id="g4-seed-difference",
        evaluator_seed=11,
    )
    second = build_external_evaluation_challenge(
        challenge_id="g4-seed-difference",
        evaluator_seed=12,
    )
    assert first.challenge_sha256 != second.challenge_sha256


def test_identified_human_authority_allows_only_bounded_advisory():
    challenge = build_external_evaluation_challenge(
        challenge_id="g4-authorized-advisory",
        evaluator_seed=101,
        requested_action=ALLOWED_ACTION,
        human_authority="independent-evaluator",
    )
    result = execute_external_evaluation_challenge(challenge)

    assert result.decisions
    assert all(decision.decision == "AUTHORIZED_ADVISORY" for decision in result.decisions)
    assert all(decision.requested_action == ALLOWED_ACTION for decision in result.decisions)


def test_missing_human_authority_forces_hold():
    challenge = build_external_evaluation_challenge(
        challenge_id="g4-human-gate",
        evaluator_seed=202,
        human_authority=None,
    )
    result = execute_external_evaluation_challenge(challenge)

    assert result.decisions
    assert all(decision.decision == "HOLD" for decision in result.decisions)
    assert not any(decision.decision == "AUTHORIZED_ADVISORY" for decision in result.decisions)


def test_prohibited_consequential_action_fails_closed():
    challenge = build_external_evaluation_challenge(
        challenge_id="g4-blocked-action",
        evaluator_seed=303,
        requested_action="fire_control_cue",
        human_authority="independent-evaluator",
    )
    result = execute_external_evaluation_challenge(challenge)

    assert result.decisions
    assert all(decision.decision == "BLOCK" for decision in result.decisions)
    assert not any(decision.decision == "AUTHORIZED_ADVISORY" for decision in result.decisions)


def test_tampered_challenge_is_rejected_before_execution():
    challenge = build_external_evaluation_challenge(
        challenge_id="g4-integrity",
        evaluator_seed=404,
    ).model_dump(mode="json")
    tampered = copy.deepcopy(challenge)
    tampered["fixture"]["observations"][0]["confidence"] = 0.01

    with pytest.raises(ValueError, match="integrity check failed"):
        execute_external_evaluation_challenge(tampered)


def test_attestation_binds_challenge_and_result_hashes():
    challenge = build_external_evaluation_challenge(
        challenge_id="g4-attestation",
        evaluator_seed=505,
    )
    result = execute_external_evaluation_challenge(challenge)
    attestation = build_external_evaluation_attestation(challenge=challenge, result=result)

    assert attestation.challenge_sha256 == challenge.challenge_sha256
    assert attestation.result_audit_sha256 == result.audit_sha256
    assert attestation.replay_sha256 == result.metrics.deterministic_replay_digest
    assert attestation.decision_counts["AUTHORIZED_ADVISORY"] >= 1
    assert len(attestation.attestation_sha256) == 64
