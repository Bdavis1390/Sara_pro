"""Reject ambiguous incoming control flags in the BAROS research boundary.

No clinical data, real patients, or authorization involved.
"""

from dataclasses import replace
import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState, decide_adaptation


def state(phase=0):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=0.95,
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
    )


def limits():
    return AdaptationThresholds(
        hypoxia_change=0.10,
        resistance_change=0.10,
        uncertainty_change=0.10,
        anatomy_change_mm=3.0,
        motion_mm=4.0,
        max_uncertainty=0.20,
        min_measurement_quality=0.80,
    )


@pytest.mark.parametrize("field,bad", [
    ("geometry_qualified", "false"),
    ("geometry_qualified", 1),
    ("geometry_qualified", None),
    ("model_identifiable", "false"),
    ("model_identifiable", 1),
    ("model_identifiable", None),
    ("out_of_distribution", "false"),
    ("out_of_distribution", 0),
    ("out_of_distribution", None),
])
def test_qualification_flags_require_actual_booleans(field, bad):
    with pytest.raises(ValueError, match=field):
        replace(state(), **{field: bad}).validate()


@pytest.mark.parametrize("bad", [0.0, 1.5, "1", True, None, -1])
def test_phase_index_must_be_nonnegative_integer_not_boolean_or_string(bad):
    with pytest.raises(ValueError, match="phase_index"):
        state(phase=bad).validate()


@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None])
def test_manual_force_requires_boolean_not_truthy_untrusted_value(bad):
    with pytest.raises(ValueError, match="manual_force"):
        decide_adaptation(
            previous=state(0),
            current=replace(state(1), hypoxia_index=(0.20, 0.45)),
            thresholds=limits(),
            last_valid_plan_identity="RESEARCH-PLAN",
            standard_plan_identity="RESEARCH-STANDARD",
            manual_force=bad,
        )


def test_qualified_boolean_input_remains_usable():
    got = decide_adaptation(
        previous=state(0),
        current=replace(state(1), hypoxia_index=(0.20, 0.45)),
        thresholds=limits(),
        last_valid_plan_identity="RESEARCH-PLAN",
        standard_plan_identity="RESEARCH-STANDARD",
        manual_force=False,
    )
    assert got.proposal_allowed is True
    assert got.treatment_authority is False
