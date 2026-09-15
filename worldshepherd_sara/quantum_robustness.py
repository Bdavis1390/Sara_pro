"""Noise/seed robustness sweeps for QRF application challengers."""

from __future__ import annotations

from dataclasses import asdict
from statistics import mean
from typing import Any, Iterable

from worldshepherd_sara.quantum_optimization import BinaryQuadraticProblem, run_benchmark


def sweep_problem(
    problem: BinaryQuadraticProblem,
    *,
    benchmark_id: str,
    instance_kind: str,
    noise_pairs: Iterable[tuple[float, float]] = ((0.001, 0.005), (0.005, 0.02), (0.01, 0.05)),
    seeds: Iterable[int] = (953, 9675, 31449),
    grid_size: int = 9,
    shots: int = 1024,
) -> dict[str, Any]:
    rows = []
    for one_error, two_error in noise_pairs:
        for seed in seeds:
            result = run_benchmark(
                problem,
                benchmark_id=benchmark_id,
                instance_kind=instance_kind,
                grid_size=grid_size,
                shots=shots,
                seed=seed,
                one_qubit_error=one_error,
                two_qubit_error=two_error,
            )
            rows.append(asdict(result))

    feasibility = [float(row["noisy_sample_feasibility_rate"]) for row in rows]
    optimal_probability = [float(row["noisy_optimal_probability"]) for row in rows]
    best_objectives = [float(row["noisy_sample_best_objective"]) for row in rows]
    optimum = float(rows[0]["exact_optimum"])
    exact_best_rate = sum(abs(value - optimum) <= 1e-12 for value in best_objectives) / len(best_objectives)

    return {
        "schema_version": "1.0",
        "benchmark_id": benchmark_id,
        "project": problem.project,
        "runs": len(rows),
        "min_noisy_feasibility_rate": min(feasibility),
        "mean_noisy_feasibility_rate": mean(feasibility),
        "min_noisy_optimal_probability": min(optimal_probability),
        "mean_noisy_optimal_probability": mean(optimal_probability),
        "run_fraction_sampling_exact_best_objective": exact_best_rate,
        "mission_use_decision": "NO_GO_BELOW_97",
        "claim_control": (
            "Robustness sweep uses a synthetic surrogate and simulator noise model. It strengthens software evidence only; "
            "it cannot replace calibrated mission instances or real hardware/relevant-environment evidence."
        ),
        "results": rows,
    }
