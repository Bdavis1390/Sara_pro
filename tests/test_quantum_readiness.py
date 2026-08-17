from worldshepherd_sara.quantum_readiness import (
    BackendClass,
    ClaimClass,
    EvidenceLevel,
    PROJECT_PROFILES,
    QuantumBackendRecord,
    QuantumDomain,
    QuantumRunEvidence,
    evaluate_run,
)


def test_simulator_cannot_become_qpu_claim():
    evidence = QuantumRunEvidence(
        project_id="WS-METASURFACE",
        experiment_id="sim-001",
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.IDEAL_SIMULATION,
        backend=QuantumBackendRecord(
            provider="local",
            backend="statevector",
            backend_class=BackendClass.STATEVECTOR,
        ),
        algorithm="QAOA benchmark",
        classical_baseline_id="baseline-001",
        result_digest="sha256:example",
    )
    decision = evaluate_run(PROJECT_PROFILES["WS-METASURFACE"], evidence)
    assert decision.accepted
    assert decision.claim_class == ClaimClass.QUANTUM_SIMULATED


def test_quantum_attribution_requires_classical_baseline():
    evidence = QuantumRunEvidence(
        project_id="WS-ALTI",
        experiment_id="qpu-001",
        domain=QuantumDomain.MATERIALS,
        evidence_level=EvidenceLevel.QPU_EXECUTED,
        backend=QuantumBackendRecord(
            provider="external-provider",
            backend="qpu-a",
            backend_class=BackendClass.QPU,
        ),
        algorithm="VQE",
        circuit_digest="sha256:circuit",
        result_digest="sha256:result",
    )
    decision = evaluate_run(PROJECT_PROFILES["WS-ALTI"], evidence)
    assert not decision.accepted
    assert "classical baseline" in " ".join(decision.reasons)


def test_glob_claim_ceiling_blocks_qpu_attribution():
    evidence = QuantumRunEvidence(
        project_id="WS-GLOB",
        experiment_id="qpu-002",
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.QPU_EXECUTED,
        backend=QuantumBackendRecord(
            provider="external-provider",
            backend="qpu-b",
            backend_class=BackendClass.QPU,
        ),
        algorithm="oracle experiment",
        classical_baseline_id="baseline-002",
        circuit_digest="sha256:circuit2",
        result_digest="sha256:result2",
    )
    decision = evaluate_run(PROJECT_PROFILES["WS-GLOB"], evidence)
    assert not decision.accepted
    assert "exceeds project ceiling" in " ".join(decision.reasons)


def test_resource_estimate_requires_qubits_and_runtime():
    evidence = QuantumRunEvidence(
        project_id="SARA-QRF",
        experiment_id="resource-001",
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.RESOURCE_ESTIMATED,
        backend=QuantumBackendRecord(
            provider="resource-estimator",
            backend="fault-tolerant-model",
            backend_class=BackendClass.RESOURCE_ESTIMATOR,
        ),
        algorithm="resource estimation",
        classical_baseline_id="baseline-003",
    )
    decision = evaluate_run(PROJECT_PROFILES["SARA-QRF"], evidence)
    assert not decision.accepted
    assert "qubit and runtime estimates" in " ".join(decision.reasons)
