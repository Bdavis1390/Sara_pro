"""Research objective-intent mapping tests with synthetic inputs only.

An abstract priority delta is NOT a prescribed dose, clinical structure,
machine parameter, TPS objective or treatment instruction.
"""

from dataclasses import replace
import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState
from baros.research_objective_intent import (
    ResearchPriorityPolicy,
    make_synthetic_research_objective_intent,
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
POLICY = ResearchPriorityPolicy(
    gain_per_index_unit=0.5, max_abstract_priority_delta=0.1
)
REGIONS = ("SYN-A", "SYN-B")


def state(phase, *, hypoxia=(0.20, 0.30), quality=0.95):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=hypoxia,
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=quality,
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
    )


def make(previous=None, current=None, **changes):
    return make_synthetic_research_objective_intent(
        previous=state(0) if previous is None else previous,
        current=state(1, hypoxia=(0.20, 0.50)) if current is None else current,
        thresholds=LIMITS,
        policy=POLICY,
        region_ids=REGIONS,
        **changes,
    )


def test_bounded_qualified_positive_biology_produces_inspectable_priority_only():
    proposal = make()
    assert proposal.decision_action == "PROPOSE_REOPTIMIZATION"
    assert proposal.proposal_allowed
    assert proposal.synthetic_policy_only
    assert proposal.treatment_authority is False
    assert proposal.dose_or_prescription_defined is False
    assert proposal.tps_export_allowed is False
    assert [x.region_id for x in proposal.region_priorities] == ["SYN-A", "SYN-B"]
    assert [x.positive_hypoxia_index_delta for x in proposal.region_priorities] == pytest.approx((0, 0.2))
    assert [x.abstract_priority_delta for x in proposal.region_priorities] == pytest.approx((0, 0.1))
    assert "do NOT generate" in proposal.next_step


@pytest.mark.parametrize("prior,current", [
    (state(0, quality=0.4), state(1, hypoxia=(0.20, 0.5))),
    (state(0), state(1, hypoxia=(0.20, 0.5), quality=0.4)),
    (replace(state(0), model_identifiable=False), state(1, hypoxia=(0.20, 0.5))),
    (state(0), replace(state(1, hypoxia=(0.20, 0.5)), geometry_qualified=False)),
    (state(0), replace(state(1, hypoxia=(0.20, 0.5)), out_of_distribution=True)),
])
def test_disqualified_either_endpoint_blocks_all_abstract_objective_values(prior, current):
    proposal = make(prior, current)
    assert not proposal.proposal_allowed
    assert proposal.region_priorities == ()
    assert not proposal.tps_export_allowed
    assert not proposal.treatment_authority


def test_no_trigger_has_no_objective_intent():
    proposal = make(current=state(1))
    assert proposal.decision_action == "NO_ADAPTATION"
    assert proposal.region_priorities == ()


def test_anatomical_trigger_alone_does_not_create_hypoxia_based_intent():
    current = replace(state(1), anatomy_delta_mm=4)
    proposal = make(current=current)
    assert proposal.proposal_allowed
    assert proposal.region_priorities == ()
    assert not proposal.tps_export_allowed


def test_decreasing_hypoxia_is_not_mislabeled_as_positive_priority():
    proposal = make(current=state(1, hypoxia=(0.20, 0.10)))
    assert proposal.proposal_allowed
    assert [x.abstract_priority_delta for x in proposal.region_priorities] == [0, 0]


def test_priority_cap_is_hard_bound_not_a_clinical_threshold():
    proposal = make(
        current=state(1, hypoxia=(0.20, 4.0)),
        policy=ResearchPriorityPolicy(1.0, 0.08),
    )
    assert proposal.region_priorities[1].abstract_priority_delta == pytest.approx(0.08)


@pytest.mark.parametrize("identifiers", [
    ("SYN-A", "SYN-A"),
    ("SYN-A",),
    ("SYN-A", "PTV70"),
    ("SYN-A", "Patient_123"),
    ("SYN-A", "SYN-TOO_LONG_NAME_TO_BE_ACCEPTED"),
    ["SYN-A", "SYN-B"],
])
def test_public_fixtures_cannot_represent_patient_or_clinical_target_names(identifiers):
    with pytest.raises(ValueError, match="synthetic|region"):
        make(region_ids=identifiers)


@pytest.mark.parametrize("policy", [
    ResearchPriorityPolicy(1.1, 0.1),
    ResearchPriorityPolicy(0.5, -0.1),
    ResearchPriorityPolicy(float("nan"), 0.1),
    ResearchPriorityPolicy(True, 0.1),
    ResearchPriorityPolicy("high", 0.1),
])
def test_nonfinite_invalid_or_ambiguous_priority_parameters_rejected(policy):
    with pytest.raises(ValueError):
        make(policy=policy)
