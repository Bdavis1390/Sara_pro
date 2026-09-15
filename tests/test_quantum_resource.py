from worldshepherd_sara.quantum_resource import (
    ResourceEstimateRecord,
    validate_resource_estimate,
)


def test_complete_resource_estimate_is_accepted():
    record = ResourceEstimateRecord(
        benchmark_id="WS-ALTI-QM-001",
        estimator_name="example-estimator",
        estimator_version="1.0",
        program_digest="sha256:" + "a" * 64,
        logical_qubits=20,
        logical_gate_count=10000,
        non_clifford_count=1200,
        target_logical_error_rate=1e-9,
        error_correction_model="surface-code-example",
        physical_qubits_estimate=50000,
        estimated_runtime_seconds=1800.0,
        code_distance=19,
        assumptions={"physical_error_rate": "1e-3"},
    )
    decision = validate_resource_estimate(record)
    assert decision.accepted
    assert decision.reasons == ()


def test_incomplete_resource_estimate_is_rejected():
    record = ResourceEstimateRecord(
        benchmark_id="WS-META-QO-001",
        estimator_name="",
        estimator_version="",
        program_digest="not-a-digest",
        logical_qubits=0,
        logical_gate_count=0,
        target_logical_error_rate=2.0,
        error_correction_model="",
        physical_qubits_estimate=0,
        estimated_runtime_seconds=0.0,
        assumptions=None,
    )
    decision = validate_resource_estimate(record)
    assert not decision.accepted
    assert len(decision.reasons) >= 7
