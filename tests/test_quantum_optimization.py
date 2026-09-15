from worldshepherd_sara.quantum_optimization import (
    exact_solve,
    logistics_surrogate_problem,
    metasurface_surrogate_problem,
    run_benchmark,
)


def test_metasurface_surrogate_has_alternating_exact_optima():
    problem = metasurface_surrogate_problem()
    optimum, states = exact_solve(problem)

    assert optimum == 0.0
    assert set(states) == {(0, 1, 0, 1), (1, 0, 1, 0)}


def test_logistics_surrogate_has_unique_lowest_cost_feasible_choice():
    problem = logistics_surrogate_problem()
    optimum, states = exact_solve(problem)

    assert optimum == 1.0
    assert states == ((0, 1, 0, 0),)
    assert problem.feasible(states[0])


def test_metasurface_qaoa_pipeline_samples_exact_optimum_without_promoting_claim():
    result = run_benchmark(
        metasurface_surrogate_problem(),
        benchmark_id="WS-META-QO-001",
        instance_kind="synthetic_reduced_order_surrogate",
        grid_size=9,
        shots=1024,
    )

    assert result.exact_optimum == 0.0
    assert result.ideal_sample_best_objective == 0.0
    assert result.noisy_sample_best_objective == 0.0
    assert result.ideal_optimal_probability > 0.0
    assert result.noisy_optimal_probability > 0.0
    assert result.promotion_decision.startswith("NOT_PROMOTED")
    assert result.result_digest.startswith("sha256:")


def test_logistics_qaoa_pipeline_keeps_feasibility_visible():
    result = run_benchmark(
        logistics_surrogate_problem(),
        benchmark_id="WS-LOG-QO-001",
        instance_kind="synthetic_assignment_surrogate",
        grid_size=9,
        shots=1024,
    )

    assert result.exact_optimum == 1.0
    assert result.ideal_sample_best_objective == 1.0
    assert result.noisy_sample_best_objective == 1.0
    assert 0.0 <= result.ideal_sample_feasibility_rate <= 1.0
    assert 0.0 <= result.noisy_sample_feasibility_rate <= 1.0
    assert result.promotion_decision.startswith("NOT_PROMOTED")
