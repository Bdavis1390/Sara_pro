import math

import numpy as np
import pytest

from baros.model_assurance import (
    ExperimentCandidate,
    assess_local_identifiability,
    assess_observability_controllability,
    expected_information_gain,
    rank_validation_experiments,
)


def test_full_rank_well_conditioned_model_is_locally_identifiable():
    result = assess_local_identifiability(
        [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
        parameter_names=("alpha", "beta"),
    )
    assert result.rank == 2
    assert result.nullity == 0
    assert result.locally_identifiable is True
    assert result.condition_number < 1e8


def test_collinear_sensitivities_expose_nonidentifiable_direction():
    result = assess_local_identifiability(
        [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]],
        parameter_names=("alpha", "beta"),
    )
    assert result.rank == 1
    assert result.nullity == 1
    assert result.locally_identifiable is False
    assert math.isinf(result.condition_number)
    assert len(result.weak_parameter_directions) == 1


def test_identifiability_rejects_invalid_shape_and_nonfinite_values():
    with pytest.raises(ValueError):
        assess_local_identifiability([[1.0, 2.0]], parameter_names=("alpha",))
    with pytest.raises(ValueError):
        assess_local_identifiability([[1.0, float("nan")]], parameter_names=("alpha", "beta"))


def test_information_gain_increases_with_more_independent_sensitivity():
    prior = [[1.0, 0.0], [0.0, 1.0]]
    weak = expected_information_gain(prior, [[1.0, 0.0]], noise_variance=1.0)
    richer = expected_information_gain(prior, [[1.0, 0.0], [0.0, 1.0]], noise_variance=1.0)
    assert richer > weak > 0.0


def test_experiment_ranking_balances_information_risk_and_cost():
    prior = [[1.0, 0.0], [0.0, 1.0]]
    ranked = rank_validation_experiments(
        prior,
        (
            ExperimentCandidate(
                name="high-information-low-risk",
                sensitivity_rows=((1.0, 0.0), (0.0, 1.0)),
                cost=0.1,
                risk=0.1,
            ),
            ExperimentCandidate(
                name="low-information",
                sensitivity_rows=((0.1, 0.0),),
                cost=0.1,
                risk=0.1,
            ),
        ),
        noise_variance=1.0,
    )
    assert ranked[0].name == "high-information-low-risk"
    assert ranked[0].utility > ranked[1].utility


def test_unauthorized_experiment_cannot_be_selected_by_utility():
    prior = [[1.0]]
    ranked = rank_validation_experiments(
        prior,
        (
            ExperimentCandidate(
                name="unauthorized-high-information",
                sensitivity_rows=((10.0,),),
                cost=0.0,
                risk=0.0,
                authorized=False,
            ),
            ExperimentCandidate(
                name="authorized",
                sensitivity_rows=((1.0,),),
                cost=0.0,
                risk=0.0,
                authorized=True,
            ),
        ),
        noise_variance=1.0,
    )
    assert ranked[0].name == "authorized"
    blocked = next(item for item in ranked if item.name.startswith("unauthorized"))
    assert blocked.authorized is False
    assert blocked.utility == -math.inf


def test_low_observability_high_control_configuration_is_flagged():
    result = assess_observability_controllability(
        observability_matrix=[[1.0, 0.0, 0.0]],
        controllability_matrix=np.eye(3),
        low_observability_threshold=0.5,
        high_controllability_threshold=0.8,
    )
    assert result.observability_fraction == pytest.approx(1 / 3)
    assert result.controllability_fraction == pytest.approx(1.0)
    assert result.low_observability_high_control_hazard is True


def test_well_observed_configuration_is_not_flagged():
    result = assess_observability_controllability(
        observability_matrix=np.eye(3),
        controllability_matrix=np.eye(3),
    )
    assert result.low_observability_high_control_hazard is False
