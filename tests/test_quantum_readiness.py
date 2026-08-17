from worldshepherd_sara.quantum_readiness import (
    BackendClass,
    ClaimClass,
    EvidenceLevel,
    PROJECT_PROFILES,
    QuantumBackendRecord,
    QuantumDomain,
    QuantumRunEvidence,
    bhattacharyya_fidelity,
    cross_backend_reproducible,
    evaluate_cross_backend_reproducibility,
    evaluate_run,
    total_variation_distance,
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


def _qpu_run(
    *,
    experiment_id: str,
    provider: str,
    backend: str,
    result_digest: str,
    distribution: dict[str, float],
    program_digest: str = "sha256:canonical-bell",
) -> QuantumRunEvidence:
    return QuantumRunEvidence(
        project_id="SARA-QRF",
        experiment_id=experiment_id,
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.QPU_EXECUTED,
        backend=QuantumBackendRecord(
            provider=provider,
            backend=backend,
            backend_class=BackendClass.QPU,
        ),
        algorithm="QRF-BELL-001",
        classical_baseline_id="bell-classical-reference-v1",
        qasm_or_qir_digest=program_digest,
        result_digest=result_digest,
        outcome_distribution=distribution,
    )


def test_distribution_metrics_normalize_counts_and_probabilities():
    counts = {"00": 490, "11": 490, "01": 10, "10": 10}
    probabilities = {"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01}
    assert total_variation_distance(counts, probabilities) == 0.0
    assert bhattacharyya_fidelity(counts, probabilities) == 1.0


def test_cross_backend_reproduction_accepts_statistical_agreement_with_distinct_results():
    left = _qpu_run(
        experiment_id="ibm-run-001",
        provider="IBM Quantum",
        backend="ibm_backend_a",
        result_digest="sha256:result-a",
        distribution={"00": 2010, "11": 1990, "01": 48, "10": 48},
    )
    right = _qpu_run(
        experiment_id="ionq-run-001",
        provider="IonQ",
        backend="forte",
        result_digest="sha256:result-b",
        distribution={"00": 1988, "11": 2005, "01": 55, "10": 48},
    )

    decision = evaluate_cross_backend_reproducibility(
        [left, right],
        max_total_variation_distance=0.03,
        min_bhattacharyya_fidelity=0.995,
    )
    assert decision.reproducible is True
    assert decision.max_total_variation_distance_observed is not None
    assert decision.max_total_variation_distance_observed < 0.03
    assert decision.min_bhattacharyya_fidelity_observed is not None
    assert decision.min_bhattacharyya_fidelity_observed > 0.995
    assert cross_backend_reproducible(
        [left, right],
        max_total_variation_distance=0.03,
        min_bhattacharyya_fidelity=0.995,
    ) is True


def test_cross_backend_reproduction_rejects_same_result_record_digest():
    left = _qpu_run(
        experiment_id="run-a",
        provider="IBM Quantum",
        backend="ibm_backend_a",
        result_digest="sha256:same-result-record",
        distribution={"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01},
    )
    right = _qpu_run(
        experiment_id="run-b",
        provider="IonQ",
        backend="forte",
        result_digest="sha256:same-result-record",
        distribution={"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01},
    )
    decision = evaluate_cross_backend_reproducibility([left, right])
    assert decision.reproducible is False
    assert any("distinct result-record digests" in reason for reason in decision.reasons)


def test_cross_backend_reproduction_rejects_different_canonical_programs():
    left = _qpu_run(
        experiment_id="run-a",
        provider="IBM Quantum",
        backend="ibm_backend_a",
        result_digest="sha256:result-a",
        distribution={"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01},
        program_digest="sha256:program-a",
    )
    right = _qpu_run(
        experiment_id="run-b",
        provider="IonQ",
        backend="forte",
        result_digest="sha256:result-b",
        distribution={"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01},
        program_digest="sha256:program-b",
    )
    decision = evaluate_cross_backend_reproducibility([left, right])
    assert decision.reproducible is False
    assert any("one canonical program digest" in reason for reason in decision.reasons)


def test_cross_backend_reproduction_rejects_statistically_divergent_results():
    left = _qpu_run(
        experiment_id="run-a",
        provider="IBM Quantum",
        backend="ibm_backend_a",
        result_digest="sha256:result-a",
        distribution={"00": 0.49, "11": 0.49, "01": 0.01, "10": 0.01},
    )
    right = _qpu_run(
        experiment_id="run-b",
        provider="IonQ",
        backend="forte",
        result_digest="sha256:result-b",
        distribution={"00": 0.25, "11": 0.25, "01": 0.25, "10": 0.25},
    )
    decision = evaluate_cross_backend_reproducibility(
        [left, right],
        max_total_variation_distance=0.10,
        min_bhattacharyya_fidelity=0.95,
    )
    assert decision.reproducible is False
    assert any("total-variation distance" in reason or "Bhattacharyya fidelity" in reason for reason in decision.reasons)


def test_cross_backend_reproduction_requires_sampled_distributions():
    left = _qpu_run(
        experiment_id="run-a",
        provider="IBM Quantum",
        backend="ibm_backend_a",
        result_digest="sha256:result-a",
        distribution={},
    )
    right = _qpu_run(
        experiment_id="run-b",
        provider="IonQ",
        backend="forte",
        result_digest="sha256:result-b",
        distribution={"00": 0.5, "11": 0.5},
    )
    decision = evaluate_cross_backend_reproducibility([left, right])
    assert decision.reproducible is False
    assert any("sampled outcome distribution" in reason for reason in decision.reasons)
