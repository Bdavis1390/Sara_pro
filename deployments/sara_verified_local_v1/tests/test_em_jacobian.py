import pytest
from pydantic import ValidationError

from worldshepherd_sara.em_jacobian import (
    DerivativeScheme,
    DiscriminatorFamily,
    DiscriminatorKind,
    JacobianCampaignRegistration,
    RegisteredDiscriminator,
    build_jacobian_plan,
)


def _continuous(**overrides) -> RegisteredDiscriminator:
    data = dict(
        parameter_id="substrate_er",
        family=DiscriminatorFamily.SUBSTRATE_RELATIVE_PERMITTIVITY,
        kind=DiscriminatorKind.CONTINUOUS,
        units="dimensionless",
        baseline_numeric_value=3.344,
        plus_numeric_value=3.4,
        derivative_scheme=DerivativeScheme.FORWARD,
        registered_before_output_inspection=True,
    )
    data.update(overrides)
    return RegisteredDiscriminator(**data)


def _campaign(discriminators, **overrides) -> JacobianCampaignRegistration:
    data = dict(
        campaign_id="uc06-jacobian-test",
        retained_baseline_model_id="uc06-retained-baseline-v1",
        retained_baseline_evidence_ref="local:sealed-baseline",
        discriminators=discriminators,
    )
    data.update(overrides)
    return JacobianCampaignRegistration(**data)


def test_forward_plan_reuses_one_18_condition_baseline() -> None:
    plan = build_jacobian_plan(_campaign([_continuous()]))
    assert plan.executable is False
    assert plan.baseline_condition_count == 18
    assert plan.perturbation_condition_count == 18
    assert len(plan.conditions) == 36
    baseline = [row for row in plan.conditions if row.condition_role == "BASELINE"]
    perturbed = [row for row in plan.conditions if row.condition_role != "BASELINE"]
    assert len(baseline) == 18
    assert len(perturbed) == 18
    assert all(row.reference_baseline_condition_id is not None for row in perturbed)


def test_central_plan_adds_minus_and_plus_against_same_baseline() -> None:
    discriminator = _continuous(
        derivative_scheme=DerivativeScheme.CENTRAL,
        minus_numeric_value=3.3,
        plus_numeric_value=3.4,
    )
    plan = build_jacobian_plan(_campaign([discriminator]))
    assert plan.baseline_condition_count == 18
    assert plan.perturbation_condition_count == 36
    assert len(plan.conditions) == 54
    roles = [row.condition_role for row in plan.conditions]
    assert roles.count("MINUS") == 18
    assert roles.count("PLUS") == 18


def test_multiple_discriminators_do_not_duplicate_baseline_matrix() -> None:
    roughness = RegisteredDiscriminator(
        parameter_id="roughness_plating_model",
        family=DiscriminatorFamily.ROUGHNESS_PLATING_MODEL,
        kind=DiscriminatorKind.CATEGORICAL_MODEL,
        baseline_model_id="uc06-retained-baseline-v1",
        alternative_model_ids=["roughness-model-a", "plating-model-b"],
        registered_before_output_inspection=True,
    )
    plan = build_jacobian_plan(_campaign([_continuous(), roughness]))
    assert plan.baseline_condition_count == 18
    assert plan.perturbation_condition_count == 54
    assert len(plan.conditions) == 72


def test_bridge_geometry_must_be_one_dimension_at_a_time() -> None:
    with pytest.raises(ValidationError):
        _continuous(
            parameter_id="bridge_gap_and_width",
            family=DiscriminatorFamily.BRIDGE_GEOMETRY,
            units="mm",
            baseline_numeric_value=0.1,
            plus_numeric_value=0.11,
        )


def test_roughness_plating_cannot_be_mislabeled_as_continuous_jacobian() -> None:
    with pytest.raises(ValidationError):
        _continuous(
            parameter_id="roughness",
            family=DiscriminatorFamily.ROUGHNESS_PLATING_MODEL,
        )


def test_categorical_baseline_must_match_retained_baseline() -> None:
    row = RegisteredDiscriminator(
        parameter_id="roughness_plating_model",
        family=DiscriminatorFamily.ROUGHNESS_PLATING_MODEL,
        kind=DiscriminatorKind.CATEGORICAL_MODEL,
        baseline_model_id="different-baseline",
        alternative_model_ids=["model-a"],
        registered_before_output_inspection=True,
    )
    with pytest.raises(ValidationError):
        _campaign([row])


def test_unregistered_perturbation_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _continuous(registered_before_output_inspection=False)


def test_open_preconditions_are_explicit_and_never_authorize_execution() -> None:
    plan = build_jacobian_plan(_campaign([_continuous()]))
    assert plan.preconditions_satisfied is False
    assert plan.executable is False
    assert plan.unresolved_preconditions == [
        "A027_A054_RECOVERY_EVIDENCE",
        "FROZEN_CONVERGENCE_ADJUDICATION",
        "ENERGY_CLOSURE_ADJUDICATION",
    ]


def test_satisfied_evidence_preconditions_still_do_not_authorize_execution() -> None:
    plan = build_jacobian_plan(
        _campaign(
            [_continuous()],
            recovery_complete_evidenced=True,
            frozen_convergence_adjudicated=True,
            energy_closure_adjudicated=True,
        )
    )
    assert plan.preconditions_satisfied is True
    assert plan.unresolved_preconditions == []
    assert plan.executable is False
