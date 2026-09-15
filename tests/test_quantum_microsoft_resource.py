from pathlib import Path

from worldshepherd_sara.quantum_microsoft_resource import estimate_file, estimate_file_sensitivity


def test_non_clifford_resource_estimate_is_estimator_backed_and_governed():
    payload = estimate_file(
        Path("benchmarks/quantum/qrf_resource_smoke.qasm"),
        benchmark_id="QRF-RESOURCE-001",
        logical_qubits=2,
        logical_gate_count=3,
    )

    record = payload["record"]
    assert payload["evidence_level"] == "resource_estimated"
    assert payload["governance"]["accepted"] is True
    assert record["estimator_name"].startswith("Microsoft Quantum Resource Estimator")
    assert record["estimator_version"] == "1.30.0"
    assert record["physical_qubits_estimate"] >= 2
    assert record["estimated_runtime_seconds"] > 0
    assert record["program_digest"].startswith("sha256:")
    assert payload["pareto_result_count"] >= 1


def test_resource_sensitivity_runs_three_governed_assumption_sets():
    payload = estimate_file_sensitivity(
        Path("benchmarks/quantum/qrf_resource_smoke.qasm"),
        benchmark_id="QRF-RESOURCE-SENS-001",
        logical_qubits=2,
        logical_gate_count=3,
    )

    assert payload["evidence_level"] == "resource_estimated_sensitivity"
    assert payload["scenario_count"] == 3
    assert payload["program_digest"].startswith("sha256:")
    assert payload["scenario_set_digest"].startswith("sha256:")
    assert payload["qec_model"] == "SurfaceCode + RoundBasedFactory"
    assert len({row["scenario_id"] for row in payload["scenarios"]}) == 3
    assert all(row["scenario_digest"].startswith("sha256:") for row in payload["scenarios"])
    assert all(row["governance"]["accepted"] is True for row in payload["scenarios"])
    assert all(row["physical_qubits_estimate"] >= 2 for row in payload["scenarios"])
    assert all(row["estimated_runtime_seconds"] > 0 for row in payload["scenarios"])
    assert payload["envelope"]["physical_qubits_max"] >= payload["envelope"]["physical_qubits_min"]
    assert payload["envelope"]["runtime_seconds_max"] >= payload["envelope"]["runtime_seconds_min"]
    assert payload["envelope"]["physical_qubits_ratio_max_to_min"] >= 1.0
    assert payload["envelope"]["runtime_ratio_max_to_min"] >= 1.0
