"""Blinded synthetic research challenge runner regression tests.

The reference labels in this test are developer-authored; they are separated
in software but are NOT independent clinical ground truth.
"""

from dataclasses import asdict, replace
import hashlib

import pytest

from baros.blinded_challenge import (
    BlindCase,
    run_blinded_challenge,
    score_after_label_release,
)
from baros.closed_loop import BiologicalState, AdaptationThresholds


EVIDENCE = hashlib.sha256(b"synthetic source only").hexdigest()

LIMITS = AdaptationThresholds(
    hypoxia_change=0.10,
    resistance_change=0.10,
    uncertainty_change=0.10,
    anatomy_change_mm=3.0,
    motion_mm=4.0,
    max_uncertainty=0.20,
    min_measurement_quality=0.80,
)


def state(phase, changed=False, *, quality=0.95):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.45) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=quality,
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
    )


def challenge():
    return (
        BlindCase("SYN-ELIGIBLE", state(0), state(1, True), LIMITS, EVIDENCE),
        BlindCase("SYN-BLOCKED", state(0), state(1, True, quality=0.4), LIMITS, EVIDENCE),
        BlindCase("SYN-NOCHANGE", state(0), state(1), LIMITS, EVIDENCE),
    )


def released_labels():
    # Not accessible to run_blinded_challenge().
    return {
        "SYN-ELIGIBLE": "qualified_trigger",
        "SYN-BLOCKED": "disqualified_trigger",
        "SYN-NOCHANGE": "no_trigger",
    }


def test_runner_keeps_labels_out_of_submission_and_replays_deterministically():
    run = run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    assert run == run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    assert len(run.results) == 3
    assert [r.proposal_allowed for r in run.results] == [True, False, False]
    assert all(not r.treatment_authority for r in run.results)
    assert len(run.submission_sha256) == 64
    assert len(run.challenge_sha256) == 64
    encoded = str(asdict(run))
    assert "qualified_trigger" not in encoded
    assert "disqualified_trigger" not in encoded
    assert "held_out_labels" not in encoded


def test_after_release_scoring_has_explicit_denominators():
    run = run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    score = score_after_label_release(run, released_labels())
    assert (score.critical_false_proceed.numerator, score.critical_false_proceed.denominator) == (0, 1)
    assert (score.eligible_proposal_recall.numerator, score.eligible_proposal_recall.denominator) == (1, 1)
    assert (score.spurious_no_trigger_proposals.numerator, score.spurious_no_trigger_proposals.denominator) == (0, 1)
    assert score.submission_sha256 == run.submission_sha256
    assert len(score.held_out_labels_sha256) == 64
    # With only one negative case, an observed zero still has a very wide interval.
    assert score.critical_false_proceed.wilson_high > 0.7


def test_tampering_with_submission_is_rejected_before_scoring():
    run = run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    corrupt = replace(run.results[1], proposal_allowed=True)
    changed = replace(run, results=(run.results[0], corrupt, run.results[2]))
    with pytest.raises(ValueError, match="integrity"):
        score_after_label_release(changed, released_labels())


def test_incomplete_and_misaligned_labels_rejected():
    run = run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    with pytest.raises(ValueError, match="exactly"):
        score_after_label_release(run, {"SYN-ELIGIBLE": "qualified_trigger"})
    with pytest.raises(ValueError, match="three"):
        score_after_label_release(run, {key: "qualified_trigger" for key in released_labels()})


def test_changing_input_changes_challenge_and_audit_commitments():
    a = run_blinded_challenge(challenge(), protocol_id="SYNTHETIC-EVALUATOR-001")
    changed_cases = list(challenge())
    changed_cases[0] = replace(
        changed_cases[0],
        previous=replace(changed_cases[0].previous, measurement_quality=0.25),
    )
    b = run_blinded_challenge(changed_cases, protocol_id="SYNTHETIC-EVALUATOR-001")
    assert a.challenge_sha256 != b.challenge_sha256
    assert a.submission_sha256 != b.submission_sha256
    assert not b.results[0].proposal_allowed


def test_duplicate_identifiers_are_rejected():
    cases = list(challenge())
    cases[1] = replace(cases[1], case_id="SYN-ELIGIBLE")
    with pytest.raises(ValueError, match="unique"):
        run_blinded_challenge(cases, protocol_id="SYNTHETIC-EVALUATOR-001")
