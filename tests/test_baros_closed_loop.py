import pytest

from baros.closed_loop import (
    AdaptationThresholds,
    BiologicalState,
    assess_triggers,
    decide_adaptation,
    phase_coupled_score,
    qualify_state,
)


def _state(
    phase,
    *,
    hypoxia=(0.20, 0.30),
    resistance=(0.10, 0.15),
    uncertainty=(0.05, 0.05),
    anatomy=0.0,
    motion=0.0,
    quality=0.95,
    geometry=True,
    identifiable=True,
    ood=False,
):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=hypoxia,
        resistance_index=resistance,
        uncertainty=uncertainty,
        anatomy_delta_mm=anatomy,
        motion_mm=motion,
        measurement_quality=quality,
        geometry_qualified=geometry,
        model_identifiable=identifiable,
        out_of_distribution=ood,
    )


def _thresholds():
    return AdaptationThresholds(
        hypoxia_change=0.10,
        resistance_change=0.10,
        uncertainty_change=0.10,
        anatomy_change_mm=3.0,
        motion_mm=4.0,
        max_uncertainty=0.20,
        min_measurement_quality=0.80,
    )


def test_biological_state_requires_aligned_voxel_arrays():
    bad = BiologicalState(
        phase_index=0,
        alpha_per_gy=(0.3,),
        beta_per_gy2=(0.03, 0.04),
        hypoxia_index=(0.2,),
        resistance_index=(0.1,),
        uncertainty=(0.05,),
    )
    with pytest.raises(ValueError, match="same non-zero length"):
        bad.validate()


def test_trigger_detects_biological_and_anatomical_change():
    previous = _state(0)
    current = _state(1, hypoxia=(0.20, 0.45), anatomy=3.2)
    result = assess_triggers(previous, current, _thresholds())
    assert result.triggered is True
    assert "hypoxia_change" in result.reasons
    assert "anatomy_change" in result.reasons


def test_no_trigger_preserves_current_governed_plan():
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1),
        thresholds=_thresholds(),
        last_valid_plan_identity="LAST-VALID",
        standard_plan_identity="STANDARD",
    )
    assert decision.action == "NO_ADAPTATION"
    assert decision.selected_plan_identity == "LAST-VALID"
    assert decision.proposal_allowed is False
    assert decision.treatment_authority is False


def test_unqualified_trigger_holds_last_valid():
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1, hypoxia=(0.20, 0.45), quality=0.50),
        thresholds=_thresholds(),
        last_valid_plan_identity="LAST-VALID",
        standard_plan_identity="STANDARD",
    )
    assert decision.action == "HOLD_LAST_VALID"
    assert "measurement_quality_below_threshold" in decision.qualification_blockers
    assert decision.proposal_allowed is False


def test_unqualified_trigger_falls_back_to_standard_without_last_valid():
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1, anatomy=4.0, ood=True),
        thresholds=_thresholds(),
        last_valid_plan_identity=None,
        standard_plan_identity="STANDARD",
    )
    assert decision.action == "FALLBACK_STANDARD"
    assert decision.selected_plan_identity == "STANDARD"
    assert "out_of_distribution" in decision.qualification_blockers


def test_qualified_trigger_only_proposes_reoptimization():
    decision = decide_adaptation(
        previous=_state(0),
        current=_state(1, resistance=(0.10, 0.30)),
        thresholds=_thresholds(),
        last_valid_plan_identity="LAST-VALID",
        standard_plan_identity="STANDARD",
    )
    assert decision.action == "PROPOSE_REOPTIMIZATION"
    assert decision.proposal_allowed is True
    assert decision.treatment_authority is False
    assert decision.selected_plan_identity == "LAST-VALID"
    assert "independent TPS or approved dose-engine recalculation" in decision.required_next_steps


def test_qualification_rejects_high_uncertainty_and_nonidentifiability():
    result = qualify_state(
        _state(1, uncertainty=(0.05, 0.30), identifiable=False),
        _thresholds(),
    )
    assert result.qualified is False
    assert "model_not_identifiable" in result.blockers
    assert "uncertainty_above_threshold" in result.blockers


def test_phase_coupling_penalizes_uncertainty_and_control_discontinuity():
    smooth = phase_coupled_score(
        phase_losses=(1.0, 0.8),
        control_vectors=((1.0, 1.0), (1.1, 1.0)),
        phase_uncertainty=(0.1, 0.1),
        uncertainty_weight=2.0,
        temporal_coupling_weight=3.0,
    )
    jump = phase_coupled_score(
        phase_losses=(1.0, 0.8),
        control_vectors=((1.0, 1.0), (2.0, 0.0)),
        phase_uncertainty=(0.1, 0.1),
        uncertainty_weight=2.0,
        temporal_coupling_weight=3.0,
    )
    assert smooth.uncertainty_penalty == pytest.approx(0.4)
    assert jump.total_score > smooth.total_score


def test_phase_coupling_rejects_mismatched_control_dimensions():
    with pytest.raises(ValueError, match="equal dimensionality"):
        phase_coupled_score(
            phase_losses=(1.0, 1.0),
            control_vectors=((1.0,), (1.0, 2.0)),
            phase_uncertainty=(0.1, 0.1),
            uncertainty_weight=1.0,
            temporal_coupling_weight=1.0,
        )
