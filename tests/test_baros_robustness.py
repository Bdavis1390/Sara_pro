import pytest

from baros.robustness import evaluate_robustness, scale_influence


def test_robustness_identifies_worst_objective_and_preserves_constraints():
    influence = (
        (1.0, 0.7, 0.2),
        (0.6, 1.0, 0.2),
    )
    scenarios = {
        "dose_minus_5pct": scale_influence(influence, 0.95),
        "nominal": influence,
        "dose_plus_5pct": scale_influence(influence, 1.05),
    }
    summary = evaluate_robustness(
        weights=(2.0, 2.0),
        influence_scenarios=scenarios,
        tumor_voxels=(0, 1),
        alpha_per_gy=(0.30, 0.25),
        beta_per_gy2=(0.03, 0.03),
        hard_max_gy={2: 1.0},
    )
    assert summary.worst_objective_scenario == "dose_minus_5pct"
    assert summary.all_hard_constraints_satisfied is True
    assert len(summary.scenarios) == 3


def test_any_hard_constraint_failure_blocks_robust_gate():
    influence = (
        (1.0, 0.7, 0.2),
        (0.6, 1.0, 0.2),
    )
    scenarios = {
        "nominal": influence,
        "high_output": scale_influence(influence, 1.50),
    }
    summary = evaluate_robustness(
        weights=(2.0, 2.0),
        influence_scenarios=scenarios,
        tumor_voxels=(0, 1),
        alpha_per_gy=(0.30, 0.25),
        beta_per_gy2=(0.03, 0.03),
        hard_max_gy={2: 1.0},
    )
    assert summary.all_hard_constraints_satisfied is False
    high = next(item for item in summary.scenarios if item.name == "high_output")
    assert high.hard_constraints_satisfied is False
    assert high.constraint_failures


def test_robustness_invalid_inputs_fail_closed():
    with pytest.raises(ValueError):
        evaluate_robustness(
            weights=(1.0,),
            influence_scenarios={},
            tumor_voxels=(0,),
            alpha_per_gy=(0.3,),
            beta_per_gy2=(0.03,),
            hard_max_gy={},
        )
    with pytest.raises(ValueError):
        scale_influence(((1.0,),), 0.0)
