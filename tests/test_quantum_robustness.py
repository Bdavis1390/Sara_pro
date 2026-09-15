from worldshepherd_sara.quantum_optimization import logistics_surrogate_problem
from worldshepherd_sara.quantum_robustness import sweep_problem


def test_robustness_sweep_retains_no_go_and_quality_metrics():
    result = sweep_problem(
        logistics_surrogate_problem(),
        benchmark_id="WS-LOG-QO-001",
        instance_kind="synthetic_assignment_surrogate",
        noise_pairs=((0.005, 0.02),),
        seeds=(9675,),
        grid_size=7,
        shots=512,
    )
    assert result["runs"] == 1
    assert 0.0 <= result["min_noisy_feasibility_rate"] <= 1.0
    assert 0.0 <= result["min_noisy_optimal_probability"] <= 1.0
    assert 0.0 <= result["run_fraction_sampling_exact_best_objective"] <= 1.0
    assert result["mission_use_decision"] == "NO_GO_BELOW_97"
