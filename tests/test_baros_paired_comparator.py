"""Paired blinded comparator software contract tests — synthetic, not clinical."""

from dataclasses import replace
import hashlib

import pytest

from baros.blinded_challenge import BlindCase, run_blinded_challenge
from baros.closed_loop import AdaptationThresholds, BiologicalState
from baros.locked_risk_coverage import RiskScore, lock_external_risk_scores
from baros.paired_comparator import compare_frozen_research_submissions


SOURCE = hashlib.sha256(b"synthetic protocol only").hexdigest()
THRESHOLDS = AdaptationThresholds(
    hypoxia_change=0.10,
    resistance_change=0.10,
    uncertainty_change=0.10,
    anatomy_change_mm=3.0,
    motion_mm=4.0,
    max_uncertainty=0.20,
    min_measurement_quality=0.80,
)
PROTOCOL = "SYNTHETIC-FOUR-CASE-BLIND"


def _state(phase, *, changed=False, good=True):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.45) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        geometry_qualified=good,
        model_identifiable=True,
        measurement_quality=0.95,
        out_of_distribution=False,
    )


def _cases():
    return (
        BlindCase("GOOD-ONE", _state(0), _state(1, changed=True), THRESHOLDS, SOURCE),
        BlindCase("BAD-ONE", _state(0), _state(1, changed=True, good=False), THRESHOLDS, SOURCE),
        BlindCase("GOOD-TWO", _state(0), _state(1, changed=True), THRESHOLDS, SOURCE),
        BlindCase("BAD-TWO", _state(0), _state(1, changed=True, good=False), THRESHOLDS, SOURCE),
    )


def _labels():
    return {
        "GOOD-ONE": "qualified_trigger",
        "BAD-ONE": "disqualified_trigger",
        "GOOD-TWO": "qualified_trigger",
        "BAD-TWO": "disqualified_trigger",
    }


def _pair(*, change_digest=False, change_ids=False, change_protocol=False):
    baros = run_blinded_challenge(_cases(), protocol_id=PROTOCOL)
    scores = (
        RiskScore("GOOD-ONE", 0.10),
        RiskScore("BAD-ONE", 0.40),
        RiskScore("GOOD-TWO", 0.50),
        RiskScore("BAD-OTHER" if change_ids else "BAD-TWO", 0.90),
    )
    external = lock_external_risk_scores(
        scores, thresholds=(0.0, 0.45, 1.0),
        protocol_id=PROTOCOL + "OTHER" if change_protocol else PROTOCOL,
        comparator_id="EXTERNALLY-SUPPLIED-SYNTHETIC-PLACEHOLDER",
        challenge_sha256="f"*64 if change_digest else baros.challenge_sha256,
    )
    return baros, external


def test_same_frozen_case_population_and_denominators():
    baros, external = _pair()
    report = compare_frozen_research_submissions(baros, external, _labels())
    assert report.challenge_sha256 == baros.challenge_sha256
    assert report.comparator_commitment_sha256 == external.commitment_sha256
    assert (report.qualified_cases, report.disqualified_cases) == (2, 2)
    zero, middle, all_cases = report.operating_points
    assert zero.comparator.proposal_coverage.numerator == 0
    assert zero.comparator.selective_failure_rate is None
    assert zero.baros_eligible_recall.numerator == 2
    assert zero.baros_false_proceed.numerator == 0
    assert zero.baros_only_eligible_proposals == 2
    assert middle.comparator.critical_false_proceed.numerator == 1
    assert middle.comparator.eligible_proposal_recall.numerator == 1
    assert middle.comparator_only_false_proceeds == 1
    assert middle.baros_only_false_proceeds == 0
    assert middle.baros_only_eligible_proposals == 1
    assert all_cases.comparator.critical_false_proceed.numerator == 2
    assert all_cases.comparator.eligible_proposal_recall.numerator == 2
    assert all_cases.comparator_only_false_proceeds == 2
    assert all_cases.baros_false_proceed.numerator == 0
    assert all_cases.baros_coverage.numerator == 2
    assert len(report.held_out_labels_sha256) == 64


@pytest.mark.parametrize("change", ["digest", "ids", "protocol"])
def test_comparator_must_match_the_same_protocol_digest_and_population(change):
    baros, external = _pair(
        change_digest=change == "digest",
        change_ids=change == "ids",
        change_protocol=change == "protocol",
    )
    with pytest.raises(ValueError):
        compare_frozen_research_submissions(baros, external, _labels())


def test_unsigned_comparator_challenge_not_accepted_for_pairwise_claim():
    baros, external = _pair()
    old = lock_external_risk_scores(
        external.risk_scores, thresholds=external.thresholds,
        protocol_id=PROTOCOL, comparator_id=external.comparator_id,
        # No challenge digest: allowed for standalone exploratory scoring, not pairwise.
    )
    with pytest.raises(ValueError, match="challenge"):
        compare_frozen_research_submissions(baros, old, _labels())


def test_forged_prediction_or_score_commitment_is_rejected():
    baros, external = _pair()
    forged = replace(baros.results[0], proposal_allowed=False)
    bad_baros = replace(baros, results=(forged, *baros.results[1:]))
    with pytest.raises(ValueError, match="integrity"):
        compare_frozen_research_submissions(bad_baros, external, _labels())
    bad_external = replace(external, thresholds=(0.1, 0.5, 1.0))
    with pytest.raises(ValueError, match="commitment"):
        compare_frozen_research_submissions(baros, bad_external, _labels())


def test_treatment_authority_cannot_enter_paired_comparison():
    baros, external = _pair()
    forged = replace(baros.results[0], treatment_authority=True)
    with pytest.raises(ValueError):
        compare_frozen_research_submissions(
            replace(baros, results=(forged, *baros.results[1:])),
            external, _labels(),
        )


def test_held_out_labels_must_cover_both_trigger_classes():
    baros, external = _pair()
    with pytest.raises(ValueError, match="same frozen"):
        compare_frozen_research_submissions(baros, external, {"GOOD-ONE":"qualified_trigger"})
    with pytest.raises(ValueError, match="triggered strata"):
        compare_frozen_research_submissions(
            baros, external, {k:"qualified_trigger" for k in _labels()},
        )
    with pytest.raises(ValueError, match="triggered strata"):
        compare_frozen_research_submissions(
            baros, external, {**_labels(), "BAD-ONE":"no_trigger"},
        )


def test_reproducible_paired_report_is_identical_for_frozen_inputs():
    b, e = _pair()
    assert compare_frozen_research_submissions(b, e, _labels()) == (
        compare_frozen_research_submissions(b, e, _labels())
    )
