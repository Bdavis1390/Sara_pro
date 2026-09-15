from worldshepherd_sara.quantum_glob_mapping import (
    GlobQuantumMapping,
    MappingType,
    evaluate_glob_mapping,
)


D = "sha256:" + "a" * 64


def test_glob_mapping_rejects_symbolic_or_incomplete_quantum_language():
    mapping = GlobQuantumMapping(
        mapping_id="GLOB-TEST",
        mapping_type=MappingType.SEARCH,
        input_contract="exact 5-digit permutation orbit",
        output_contract="target membership boolean",
        measurable_target="query complexity versus exact enumeration",
        classical_baseline="exact enumeration",
        classical_complexity="O(N)",
        quantum_object_digest=D,
        construction_cost="oracle construction counted explicitly",
        verification_method="compare all small instances to exact enumeration",
    )
    decision = evaluate_glob_mapping(mapping)
    assert not decision.admissible_for_quantum_experiment
    assert "null/randomized model is required before quantum attribution" in decision.reasons
    assert "resource estimate is required before QPU execution is justified" in decision.reasons


def test_complete_glob_mapping_can_enter_experiment_queue_but_remains_no_go_mission_use():
    mapping = GlobQuantumMapping(
        mapping_id="GLOB-TEST-2",
        mapping_type=MappingType.SEARCH,
        input_contract="finite indexed set",
        output_contract="marked-index sample",
        measurable_target="query count",
        classical_baseline="exact search",
        classical_complexity="O(N)",
        quantum_object_digest=D,
        construction_cost="O(N) preprocessing explicitly charged",
        verification_method="exact small-instance comparison",
        resource_estimate_id="QRE-1",
        null_model_id="NULL-1",
    )
    decision = evaluate_glob_mapping(mapping)
    assert decision.admissible_for_quantum_experiment
    assert decision.mission_use_decision == "NO_GO_BELOW_97"
