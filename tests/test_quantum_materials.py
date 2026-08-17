from worldshepherd_sara.quantum_materials import run_materials_benchmark


def test_small_materials_hamiltonian_exact_vs_variational_pipeline():
    # Deliberately generic two-qubit reference Hamiltonian, not an Al-Ti claim.
    result = run_materials_benchmark(
        {"ZI": -1.0, "IZ": -0.8, "XX": 0.15},
        benchmark_id="QRF-MATERIALS-PIPELINE-001",
        grid_points=13,
    )
    assert result.qubits == 2
    assert result.variational_best_energy >= result.exact_ground_energy - 1e-10
    assert result.absolute_energy_error >= 0.0
    assert result.parameter_points_evaluated == 13 * 13
    assert result.hamiltonian_digest.startswith("sha256:")
    assert result.mission_use_decision.startswith("NO_GO_BELOW_97")
