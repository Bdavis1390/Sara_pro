from pathlib import Path

from worldshepherd_sara.quantum_microsoft_resource import estimate_file


def test_bell_resource_estimate_is_estimator_backed_and_governed():
    payload = estimate_file(
        Path("benchmarks/quantum/bell_qasm3.qasm"),
        benchmark_id="QRF-BELL-001",
        logical_qubits=2,
        logical_gate_count=2,
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
