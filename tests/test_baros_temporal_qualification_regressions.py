"""Adversarial temporal qualification regressions for BAROS research controller.

Synthetic tests only. These enforce software semantics, not biomarker validity,
physical dose accuracy, or clinical treatment authorization.
"""

from dataclasses import replace
import pytest

from baros.closed_loop import (
    AdaptationThresholds,
    BiologicalState,
    assess_triggers,
    decide_adaptation,
)

LIMITS = AdaptationThresholds(
    hypoxia_change=0.10,
    resistance_change=0.10,
    uncertainty_change=0.10,
    anatomy_change_mm=3.0,
    motion_mm=4.0,
    max_uncertainty=0.20,
    min_measurement_quality=0.80,
)


def state(phase, *, changed=False, **changes):
    baseline = BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.46) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
        measurement_quality=0.95,
    )
    return replace(baseline, **changes)


def decision(prior, current, thresholds=LIMITS, *, force=False):
    return decide_adaptation(
        previous=prior,
        current=current,
        thresholds=thresholds,
        last_valid_plan_identity="PREVIOUS-RESEARCH-PLAN",
        standard_plan_identity="STANDARD-RESEARCH-PLAN",
        manual_force=force,
    )


@pytest.mark.parametrize("prior_change,reason", [
    ({"geometry_qualified": False}, "previous_geometry_not_qualified"),
    ({"model_identifiable": False}, "previous_model_not_identifiable"),
    ({"out_of_distribution": True}, "previous_out_of_distribution"),
    ({"measurement_quality": 0.20}, "previous_measurement_quality_below_threshold"),
    ({"uncertainty": (0.05, 0.35)}, "previous_uncertainty_above_threshold"),
])
def test_unqualified_prior_cannot_authorize_change_from_good_current(prior_change, reason):
    previous = state(0, **prior_change)
    current = state(1, changed=True)
    got = decision(previous, current)
    assert got.triggered
    assert got.action == "HOLD_LAST_VALID"
    assert not got.proposal_allowed
    assert not got.treatment_authority
    assert got.selected_plan_identity == "PREVIOUS-RESEARCH-PLAN"
    assert reason in got.qualification_blockers


def test_manual_force_does_not_override_unqualified_prior():
    got = decision(state(0, model_identifiable=False), state(1), force=True)
    assert got.triggered
    assert got.action == "HOLD_LAST_VALID"
    assert not got.proposal_allowed
    assert "previous_model_not_identifiable" in got.qualification_blockers


def test_both_timepoints_qualified_still_permit_research_proposal():
    got = decision(state(0), state(1, changed=True))
    assert got.action == "PROPOSE_REOPTIMIZATION"
    assert got.proposal_allowed
    assert not got.treatment_authority


def test_unqualified_prior_no_trigger_is_recorded_but_not_promoted():
    got = decision(state(0, measurement_quality=0.2), state(1))
    assert not got.proposal_allowed
    assert "previous_measurement_quality_below_threshold" in got.qualification_blockers
    assert not got.treatment_authority


def test_zero_thresholds_do_not_turn_unchanged_observations_into_triggers():
    limits = replace(
        LIMITS,
        hypoxia_change=0.0,
        resistance_change=0.0,
        uncertainty_change=0.0,
        anatomy_change_mm=0.0,
        motion_mm=0.0,
    )
    prior, current = state(0), state(1)
    trigger = assess_triggers(prior, current, limits)
    assert not trigger.triggered
    got = decision(prior, current, limits)
    assert got.action == "NO_ADAPTATION"
    assert not got.proposal_allowed
    assert got.trigger_reasons == ()


def test_zero_threshold_detects_actual_nonzero_change():
    limits = replace(LIMITS, hypoxia_change=0.0)
    got = decision(state(0), state(1, changed=True), limits)
    assert got.action == "PROPOSE_REOPTIMIZATION"
    assert "hypoxia_change" in got.trigger_reasons
    assert not got.treatment_authority
