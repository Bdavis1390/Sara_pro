"""BAROS Phase-I pre-TPS research qualification: deterministic negative-control matrix.

Research-only synthetic fixtures. These tests DO NOT establish clinical safety,
dose accuracy, model validity, TPS interoperability, or treatment effectiveness.
The fixture author and product developer are not independent evaluators.
"""

from itertools import product

import pytest

from baros.closed_loop import (
    AdaptationThresholds,
    BiologicalState,
    decide_adaptation,
)


def _state(phase, *, changed=False, geometry=True, identifiable=True,
           ood=False, quality=0.95, uncertainty=0.05):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.45) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(uncertainty, uncertainty),
        measurement_quality=quality,
        geometry_qualified=geometry,
        model_identifiable=identifiable,
        out_of_distribution=ood,
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


@pytest.mark.parametrize(
    "geometry,identifiable,ood,quality,uncertainty",
    list(product((True, False), (True, False), (False, True),
                 (0.95, 0.50), (0.05, 0.30))),
)
def test_five_dimensional_negative_control_matrix(
    geometry, identifiable, ood, quality, uncertainty
):
    """All 32 combinations: only entirely qualified cases may propose."""
    qualified = (geometry and identifiable and not ood
                 and quality >= 0.80 and uncertainty <= 0.20)
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1, changed=True, geometry=geometry,
                       identifiable=identifiable, ood=ood,
                       quality=quality, uncertainty=uncertainty),
        thresholds=LIMITS,
        last_valid_plan_identity="LOCKED-LAST-VALID",
        standard_plan_identity="LOCKED-STANDARD",
    )
    assert decision.triggered
    assert decision.proposal_allowed is qualified
    assert decision.treatment_authority is False
    assert decision.selected_plan_identity == "LOCKED-LAST-VALID"
    assert decision.action == (
        "PROPOSE_REOPTIMIZATION" if qualified else "HOLD_LAST_VALID"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"geometry": False},
        {"identifiable": False},
        {"ood": True},
        {"quality": 0.50},
        {"uncertainty": 0.30},
    ],
)
def test_manual_force_cannot_override_any_disqualifying_input(changes):
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1, changed=False, **changes),
        thresholds=LIMITS,
        last_valid_plan_identity=None,
        standard_plan_identity="LOCKED-STANDARD",
        manual_force=True,
    )
    assert decision.triggered
    assert decision.action == "FALLBACK_STANDARD"
    assert not decision.proposal_allowed
    assert not decision.treatment_authority
    assert decision.selected_plan_identity == "LOCKED-STANDARD"


def test_no_trigger_does_not_propose_even_with_qualified_input():
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1),
        thresholds=LIMITS,
        last_valid_plan_identity="LOCKED-LAST-VALID",
        standard_plan_identity="LOCKED-STANDARD",
    )
    assert decision.action == "NO_ADAPTATION"
    assert decision.proposal_allowed is False
    assert decision.treatment_authority is False


@pytest.mark.parametrize("phase", (0, -1))
def test_out_of_order_or_invalid_phase_is_rejected(phase):
    with pytest.raises(ValueError):
        decide_adaptation(
            previous=_state(0),
            current=_state(phase, changed=True),
            thresholds=LIMITS,
            last_valid_plan_identity="LOCKED-LAST-VALID",
            standard_plan_identity="LOCKED-STANDARD",
        )


@pytest.mark.parametrize("uncertainty", (float("nan"), float("inf"), -0.01))
def test_nonfinite_or_negative_uncertainty_is_rejected(uncertainty):
    with pytest.raises(ValueError):
        decide_adaptation(
            previous=_state(0),
            current=_state(1, changed=True, uncertainty=uncertainty),
            thresholds=LIMITS,
            last_valid_plan_identity="LOCKED-LAST-VALID",
            standard_plan_identity="LOCKED-STANDARD",
        )
