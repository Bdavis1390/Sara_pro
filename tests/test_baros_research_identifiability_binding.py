"""Toy identifiability binding tests: research only, NOT biological validation."""

import hashlib

import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState, decide_adaptation
from baros.research_identifiability_binding import bind_research_identifiability


SOURCE = hashlib.sha256(b"synthetic-model-sensitivity-v1").hexdigest()


def state(phase, *, changed=False):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.45) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        geometry_qualified=True,
        measurement_quality=0.95,
        model_identifiable=True,  # untrusted caller assertion intentionally
    )


def thresholds():
    return AdaptationThresholds(
        hypoxia_change=0.10,
        resistance_change=0.10,
        uncertainty_change=0.10,
        anatomy_change_mm=3.0,
        motion_mm=4.0,
        max_uncertainty=0.20,
        min_measurement_quality=0.80,
    )


def decide(current):
    return decide_adaptation(
        previous=state(0),
        current=current,
        thresholds=thresholds(),
        last_valid_plan_identity="RESEARCH-LAST-VALID",
        standard_plan_identity="RESEARCH-STANDARD",
    )


def test_rank_deficiency_overrides_untrusted_identifiable_flag():
    bound = bind_research_identifiability(
        state=state(1, changed=True),
        jacobian=((1.0, 2.0), (2.0, 4.0), (3.0, 6.0)),
        parameter_names=("synthetic_a", "synthetic_b"),
        reported_source_sha256=SOURCE,
    )
    assert bound.assessment.rank == 1
    assert bound.assessment.locally_identifiable is False
    assert bound.state.model_identifiable is False
    decision = decide(bound.state)
    assert decision.action == "HOLD_LAST_VALID"
    assert not decision.proposal_allowed
    assert not decision.treatment_authority


def test_full_rank_synthetic_matrix_can_propose_but_never_treat():
    bound = bind_research_identifiability(
        state=state(1, changed=True),
        jacobian=((1., 0.), (0., 1.), (1., 1.)),
        parameter_names=("synthetic_a", "synthetic_b"),
        reported_source_sha256=SOURCE,
    )
    assert bound.assessment.locally_identifiable
    assert bound.state.model_identifiable
    d = decide(bound.state)
    assert d.action == "PROPOSE_REOPTIMIZATION"
    assert not d.treatment_authority


def test_binding_hash_changes_with_matrix_and_source():
    kwargs = dict(
        state=state(1, changed=True),
        parameter_names=("synthetic_a", "synthetic_b"),
        reported_source_sha256=SOURCE,
    )
    a = bind_research_identifiability(jacobian=((1., 0.), (0., 1.)), **kwargs)
    b = bind_research_identifiability(jacobian=((1., 0.), (0., 2.)), **kwargs)
    c = bind_research_identifiability(
        jacobian=((1., 0.), (0., 1.)),
        **{**kwargs, "reported_source_sha256": "f" * 64},
    )
    assert a.binding_sha256 != b.binding_sha256
    assert a.binding_sha256 != c.binding_sha256
    assert a == bind_research_identifiability(jacobian=((1., 0.), (0., 1.)), **kwargs)


@pytest.mark.parametrize("bad", ("", "unknown", "A" * 64))
def test_invalid_measurement_digest_rejected(bad):
    with pytest.raises(ValueError, match="source_sha256"):
        bind_research_identifiability(
            state=state(1, changed=True),
            jacobian=((1., 0.), (0., 1.)),
            parameter_names=("a", "b"),
            reported_source_sha256=bad,
        )


def test_nonfinite_sensitivity_rejected():
    with pytest.raises(ValueError):
        bind_research_identifiability(
            state=state(1, changed=True),
            jacobian=((float("nan"), 0.), (0., 1.)),
            parameter_names=("a", "b"),
            reported_source_sha256=SOURCE,
        )
