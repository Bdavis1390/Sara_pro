"""Synthetic BAROS comparator test: no clinical performance conclusions."""

import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState
from baros.phase1_evaluation import PredeclaredCase, evaluate_cases


LIMITS = AdaptationThresholds(
    hypoxia_change=0.10,
    resistance_change=0.10,
    uncertainty_change=0.10,
    anatomy_change_mm=3.0,
    motion_mm=4.0,
    max_uncertainty=0.20,
    min_measurement_quality=0.80,
)


def _state(phase, *, hypoxia=(0.20, 0.30), quality=0.95, geometry=True,
           identifiable=True, ood=False, uncertainty=(0.05, 0.05)):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=hypoxia,
        resistance_index=(0.10, 0.15),
        uncertainty=uncertainty,
        measurement_quality=quality,
        geometry_qualified=geometry,
        model_identifiable=identifiable,
        out_of_distribution=ood,
    )


def _cases():
    baseline = _state(0)
    cases = []
    # Exactly five predeclared qualified triggers: eligible proposals.
    for i, upper in enumerate((0.42, 0.44, 0.46, 0.48, 0.50)):
        cases.append(PredeclaredCase(
            case_id=f"eligible_{i}", truth="qualified_trigger",
            previous=baseline, current=_state(1, hypoxia=(0.20, upper)),
        ))
    # Exactly five triggered cases predeclared disqualified under distinct controls.
    defects = (
        {"quality": 0.50},
        {"geometry": False},
        {"identifiable": False},
        {"ood": True},
        {"uncertainty": (0.05, 0.30)},
    )
    for i, override in enumerate(defects):
        cases.append(PredeclaredCase(
            case_id=f"disqualified_{i}", truth="disqualified_trigger",
            previous=baseline,
            current=_state(1, hypoxia=(0.20, 0.45), **override),
        ))
    cases.append(PredeclaredCase(
        "no_trigger_qualified", "no_trigger", baseline, _state(1),
    ))
    cases.append(PredeclaredCase(
        "no_trigger_low_quality", "no_trigger", baseline, _state(1, quality=0.50),
    ))
    return cases


def test_comparators_make_both_false_proceed_and_overabstention_visible():
    report = evaluate_cases(_cases(), LIMITS)
    assert report.cases == 12
    assert (report.eligible_cases, report.disqualified_cases, report.no_trigger_cases) == (5, 5, 2)
    gated, trigger_only, abstain_all = report.results
    assert [r.strategy for r in report.results] == ["gated", "trigger_only", "abstain_all"]

    assert (gated.critical_false_proceed.numerator, gated.critical_false_proceed.denominator) == (0, 5)
    assert (gated.eligible_proposal_recall.numerator, gated.eligible_proposal_recall.denominator) == (5, 5)
    assert gated.spurious_proposals_without_trigger.numerator == 0

    assert trigger_only.critical_false_proceed.numerator == 5
    assert trigger_only.eligible_proposal_recall.numerator == 5
    assert abstain_all.critical_false_proceed.numerator == 0
    assert abstain_all.eligible_proposal_recall.numerator == 0
    assert not report.treatment_authority_ever_granted


def test_zero_failures_still_have_uncertain_bounded_rate():
    report = evaluate_cases(_cases(), LIMITS)
    rate = report.results[0].critical_false_proceed
    assert rate.value == 0
    assert rate.wilson_low == 0
    # This interval is only descriptive for developer-authored cases.
    assert 0.3 < rate.wilson_high < 0.6


@pytest.mark.parametrize("mutator", [
    lambda cases: cases[:1],
    lambda cases: cases[:-1] + [cases[0]],
    lambda cases: cases[:-1] + [PredeclaredCase("", "no_trigger", _state(0), _state(1))],
])
def test_invalid_challenge_sets_are_not_silently_scored(mutator):
    with pytest.raises(ValueError):
        evaluate_cases(mutator(_cases()), LIMITS)
