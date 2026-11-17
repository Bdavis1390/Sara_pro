"""Locked score benchmark checks; all fixtures are developer-authored synthetics.

No claim that these scores were created by a peer-reviewed uncertainty model.
"""

from dataclasses import replace
import pytest

from baros.locked_risk_coverage import (
    RiskScore,
    lock_external_risk_scores,
    score_external_after_unblinding,
)


def fixtures():
    return (
        RiskScore("synthetic-good-low", 0.05),
        RiskScore("synthetic-bad-high", 0.95),
        RiskScore("synthetic-good-medium", 0.40),
        RiskScore("synthetic-bad-mid", 0.65),
    )


def labels():
    return {
        "synthetic-good-low": "qualified_trigger",
        "synthetic-bad-high": "disqualified_trigger",
        "synthetic-good-medium": "qualified_trigger",
        "synthetic-bad-mid": "disqualified_trigger",
    }


def lock(scores=None, thresholds=(0.0, 0.5, 0.7, 1.0)):
    return lock_external_risk_scores(
        fixtures() if scores is None else scores,
        thresholds=thresholds,
        protocol_id="SYNTHETIC-FROZEN-REVIEW",
        comparator_id="SYNTHETIC-EXTERNAL-SCORE-PLACEHOLDER",
    )


def test_locked_thresholds_produce_all_predeclared_operating_points():
    submitted = lock()
    assert lock() == submitted
    report = score_external_after_unblinding(submitted, labels())
    assert len(report.operating_points) == 4
    zero, half, seven, allcases = report.operating_points
    assert zero.proposal_coverage.numerator == 0
    assert zero.selective_failure_rate is None
    assert zero.eligible_proposal_recall.numerator == 0
    assert half.proposal_coverage.numerator == 2
    assert half.critical_false_proceed.numerator == 0
    assert half.eligible_proposal_recall.numerator == 2
    assert half.selective_failure_rate.value == 0.0
    assert seven.proposal_coverage.numerator == 3
    assert seven.critical_false_proceed.numerator == 1
    assert seven.selective_failure_rate.numerator == 1
    assert allcases.proposal_coverage.numerator == 4
    assert allcases.critical_false_proceed.numerator == 2
    assert allcases.selective_failure_rate.numerator == 2
    assert all(not p.selective_failure_rate or p.selective_failure_rate.denominator > 0
               for p in report.operating_points)


def test_tampering_with_scores_and_thresholds_is_detected():
    old = lock()
    altered = list(old.risk_scores)
    altered[0] = replace(altered[0], risk=0.91)
    with pytest.raises(ValueError, match="commitment"):
        score_external_after_unblinding(replace(old, risk_scores=tuple(altered)), labels())
    with pytest.raises(ValueError, match="commitment"):
        score_external_after_unblinding(replace(old, thresholds=(0.1, 0.5, 0.7, 1.0)), labels())


@pytest.mark.parametrize("scores", [
    (RiskScore("a", float("nan")),),
    (RiskScore("a", float("inf")),),
    (RiskScore("a", -0.01),),
    (RiskScore("a", 1.01),),
    (RiskScore("a", True),),
    (RiskScore("a", "0.2"),),
    (RiskScore("a", 0.2), RiskScore("a", 0.3)),
])
def test_nonfinite_out_of_range_or_ambiguous_scores_rejected(scores):
    with pytest.raises(ValueError):
        lock(scores)


@pytest.mark.parametrize("thresholds", [
    (), (-0.1,), (1.1,), (float("nan"),), ("0.4",),
    (0.7, 0.4), (0.4, 0.4), (True,),
])
def test_unfrozen_or_invalid_threshold_grid_rejected(thresholds):
    with pytest.raises(ValueError):
        lock(thresholds=thresholds)


def test_missing_extraneous_or_single_stratum_labels_rejected():
    submitted = lock()
    with pytest.raises(ValueError, match="exactly"):
        score_external_after_unblinding(submitted, {"synthetic-good-low": "qualified_trigger"})
    with pytest.raises(ValueError, match="both"):
        score_external_after_unblinding(
            submitted, {key: "qualified_trigger" for key in labels()}
        )


def test_threshold_inclusivity_is_explicit():
    submitted = lock(thresholds=(0.05,))
    report = score_external_after_unblinding(submitted, labels())
    assert report.operating_points[0].proposal_coverage.numerator == 1


def test_identical_scores_and_thresholds_produce_same_commitment():
    first = lock()
    second = lock()
    assert first.commitment_sha256 == second.commitment_sha256
    assert len(first.commitment_sha256) == 64
