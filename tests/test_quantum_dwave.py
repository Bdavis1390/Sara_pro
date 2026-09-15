import pytest

from worldshepherd_sara.quantum_dwave import (
    DWaveAnnealResult,
    build_dwave_mission_optimization_evidence,
    qubo_digest,
    run_qubo_on_dwave_hardware,
)
from worldshepherd_sara.quantum_external_evidence import validate_external_evidence


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _result(**overrides):
    payload = dict(
        provider="D-Wave Leap",
        modality="quantum_annealing",
        solver_name="Advantage2_system_fixture",
        solver_identity={"name": "Advantage2_system_fixture", "version": {"graph_id": "fixture-graph"}},
        solver_identity_digest=SHA_A,
        solver_properties_digest=SHA_B,
        problem_digest=SHA_C,
        num_reads=1000,
        best_sample={"0": 0, "1": 1},
        best_energy=-1.0,
        samples=(
            {"sample": {"0": 0, "1": 1}, "energy": -1.0, "num_occurrences": 700},
            {"sample": {"0": 1, "1": 0}, "energy": -1.0, "num_occurrences": 300},
        ),
        timing={"qpu_sampling_time": 1000.0, "qpu_access_time": 2000.0},
        timing_digest=SHA_D,
        embedding_context={"embedding": {"0": [1], "1": [2]}},
        result_digest=SHA_E,
        wall_latency_seconds=3.5,
        executed_at_utc="2026-08-17T17:10:00Z",
        ocean_version="9.4.0",
    )
    payload.update(overrides)
    return DWaveAnnealResult(**payload)


def test_dwave_hardware_adapter_requires_runtime_token_before_optional_import():
    with pytest.raises(ValueError, match="token"):
        run_qubo_on_dwave_hardware({(0, 0): -1.0}, token="")


def test_qubo_digest_is_order_invariant_for_same_mapping_terms():
    left = {(0, 0): -1.0, (0, 1): 2.0, (1, 1): -1.0}
    right = {(1, 1): -1.0, (0, 1): 2.0, (0, 0): -1.0}
    assert qubo_digest(left) == qubo_digest(right)
    assert qubo_digest(left).startswith("sha256:")


def test_dwave_result_requires_frozen_mission_family_and_classical_baseline():
    with pytest.raises(ValueError, match="instance_family_digest"):
        build_dwave_mission_optimization_evidence(
            _result(),
            project_id="WS-AUTONOMOUS-LOGISTICS",
            campaign_gate_id="WS-AUTONOMOUS-LOGISTICS-EXT-01",
            classical_baseline_digest=SHA_A,
            instance_family_digest="",
            objective_definition="minimize mission cost",
            constraint_definition="frozen mission constraints",
            cost_usd=0.0,
        )


def test_dwave_result_converts_to_structurally_valid_mission_optimization_record():
    evidence = build_dwave_mission_optimization_evidence(
        _result(),
        project_id="WS-AUTONOMOUS-LOGISTICS",
        campaign_gate_id="WS-AUTONOMOUS-LOGISTICS-EXT-01",
        classical_baseline_digest=SHA_A,
        instance_family_digest=SHA_B,
        objective_definition="minimize frozen mission objective",
        constraint_definition="satisfy frozen mission constraints",
        cost_usd=12.34,
    )
    decision = validate_external_evidence(evidence)

    assert decision.accepted_for_intake is True
    assert evidence.provider_or_lab == "D-Wave Leap"
    assert evidence.backend_or_device == "Advantage2_system_fixture"
    assert evidence.metadata["quantum_modality"] == "quantum_annealing"
    assert evidence.metadata["campaign_gate_id"] == "WS-AUTONOMOUS-LOGISTICS-EXT-01"
    assert evidence.metadata["solver_identity_digest"] == SHA_A
    assert evidence.metadata["embedding_retained"] == "true"
    assert evidence.classical_baseline_digest == SHA_A
    assert evidence.cost_usd == 12.34


def test_dwave_evidence_does_not_relabel_annealing_as_gate_model_qpu_execution():
    evidence = build_dwave_mission_optimization_evidence(
        _result(),
        project_id="WS-AUTONOMOUS-LOGISTICS",
        campaign_gate_id="WS-AUTONOMOUS-LOGISTICS-EXT-01",
        classical_baseline_digest=SHA_A,
        instance_family_digest=SHA_B,
        objective_definition="minimize frozen mission objective",
        constraint_definition="satisfy frozen mission constraints",
        cost_usd=0.0,
    )
    assert evidence.evidence_type.value == "mission_optimization"
    assert evidence.metadata["quantum_modality"] == "quantum_annealing"
