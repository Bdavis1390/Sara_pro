from worldshepherd_sara.quantum_qiskit import run_bell_simulation


def test_ideal_bell_simulation_is_correlated_and_digestible():
    result = run_bell_simulation(shots=2048, seed=9675, noisy=False)
    assert result.correlated_fraction == 1.0
    assert set(result.counts).issubset({"00", "11"})
    assert result.result_digest.startswith("sha256:")


def test_noisy_bell_simulation_exposes_degradation():
    result = run_bell_simulation(
        shots=4096,
        seed=9675,
        noisy=True,
        one_qubit_error=0.05,
        two_qubit_error=0.15,
    )
    assert 0.5 < result.correlated_fraction < 1.0
    assert result.counts.get("01", 0) + result.counts.get("10", 0) > 0
    assert result.noise_model["two_qubit_depolarizing"] == 0.15
