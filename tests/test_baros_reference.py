import math
import pytest

from baros import (
    dose_from_influence,
    hard_max_constraints,
    logistic_ntcp,
    lq_survival,
    optimize_synthetic,
    poisson_tcp,
    tumor_survival_objective,
)


def test_lq_survival_known_case():
    assert lq_survival(2.0, 0.3, 0.03) == pytest.approx(math.exp(-0.72))
    assert lq_survival(0.0, 0.3, 0.03) == pytest.approx(1.0)


def test_poisson_tcp_known_case():
    expected = math.exp(-(10.0 * 0.1 + 5.0 * 0.2))
    assert poisson_tcp([10.0, 5.0], [0.1, 0.2]) == pytest.approx(expected)


def test_logistic_ntcp_is_half_at_d50_and_monotonic():
    assert logistic_ntcp(50.0, 50.0, 0.2) == pytest.approx(0.5)
    assert logistic_ntcp(40.0, 50.0, 0.2) < 0.5
    assert logistic_ntcp(60.0, 50.0, 0.2) > 0.5


def test_dose_matrix_and_hard_constraint_fail_closed():
    influence = [[1.0, 0.1, 0.5], [0.5, 0.1, 1.0]]
    dose = dose_from_influence([2.0, 1.0], influence)
    assert dose == pytest.approx([2.5, 0.3, 2.0])
    ok, failures = hard_max_constraints(dose, {1: 0.31})
    assert ok and not failures
    ok, failures = hard_max_constraints(dose, {1: 0.29})
    assert not ok and "exceeds max" in failures[0]


def test_optimizer_improves_tumor_survival_without_breaking_oar_limit():
    influence = [
        [1.0, 0.7, 0.30],
        [0.6, 1.0, 0.20],
    ]
    initial = [0.0, 0.0]
    initial_dose = dose_from_influence(initial, influence)
    initial_obj = tumor_survival_objective(initial_dose, [0, 1], [0.30, 0.25], [0.03, 0.03])

    result = optimize_synthetic(
        influence=influence,
        tumor_voxels=[0, 1],
        alpha_per_gy=[0.30, 0.25],
        beta_per_gy2=[0.03, 0.03],
        oar_max_gy={2: 2.0},
        initial_weights=initial,
        weight_max=20.0,
        step_size=5.0,
        max_iterations=200,
    )

    assert result.objective < initial_obj
    ok, failures = hard_max_constraints(result.dose_gy, {2: 2.0})
    assert ok, failures
    assert result.dose_gy[0] > 0.0 and result.dose_gy[1] > 0.0


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        lq_survival(-1.0, 0.3, 0.03)
    with pytest.raises(ValueError):
        dose_from_influence([1.0], [[1.0], [2.0]])
    with pytest.raises(ValueError):
        optimize_synthetic(
            influence=[[1.0, 1.0]],
            tumor_voxels=[0],
            alpha_per_gy=[0.3],
            beta_per_gy2=[0.03],
            oar_max_gy={1: 0.1},
            initial_weights=[1.0],
        )
