from pathlib import Path

from worldshepherd_sara.quantum_logistics_instance import (
    ClassicalBaselineRecord,
    MissionInstanceFamilyRecord,
    artifact_digest,
    evaluate_logistics_gate,
    logistics_template_as_dict,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _family(instance_path: Path) -> MissionInstanceFamilyRecord:
    return MissionInstanceFamilyRecord(
        project_id="WS-AUTONOMOUS-LOGISTICS",
        family_id="WS-LOG-FIXTURE-001",
        mission_source="synthetic-test-fixture://mission-family",
        mission_scope="software validator fixture for multi-vehicle constrained assignment",
        instance_count=3,
        vehicle_count_range=(2, 4),
        task_count_range=(5, 9),
        objective_definition="minimize weighted time + infeasibility penalty fixture",
        constraint_definition="capacity, assignment, time-window and disruption constraints fixture",
        objective_digest=SHA_A,
        constraint_digest=SHA_B,
        instance_family_digest=SHA_A,
        raw_instance_artifact_digest=artifact_digest(instance_path),
        units_definition="normalized distance/time/capacity fixture units",
        latency_budget_seconds=5.0,
        degraded_state_definition="one vehicle or communication edge removed per disruption case",
        disruption_scenario_count=2,
        data_rights_or_provenance="synthetic unit-test fixture",
    )


def _baseline(family: MissionInstanceFamilyRecord, result_path: Path) -> ClassicalBaselineRecord:
    return ClassicalBaselineRecord(
        project_id=family.project_id,
        family_id=family.family_id,
        instance_family_digest=family.instance_family_digest,
        solver_name="fixture exact solver",
        solver_version="1.0",
        solver_class="exhaustive/MILP fixture",
        configuration_digest=SHA_B,
        result_digest=SHA_A,
        result_artifact_digest=artifact_digest(result_path),
        instances_solved=3,
        feasible_instances=3,
        optimality_or_gap_definition="exact optimum fixture",
        objective_summary="three feasible exact reference objectives",
        wall_time_seconds=0.1,
        hardware_description="CI CPU fixture",
        test_protocol_digest=SHA_B,
    )


def test_logistics_gate_requires_real_instance_and_result_artifacts(tmp_path):
    instance_path = tmp_path / "instances.json"
    result_path = tmp_path / "baseline.json"
    instance_path.write_text('{"instances":[1,2,3]}', encoding="utf-8")
    result_path.write_text('{"results":[1,2,3]}', encoding="utf-8")
    family = _family(instance_path)
    baseline = _baseline(family, result_path)

    blocked = evaluate_logistics_gate(family, baseline)
    assert blocked.accepted is False
    assert any("actual mission-instance artifact is required" in reason for reason in blocked.reasons)
    assert any("actual classical baseline result artifact is required" in reason for reason in blocked.reasons)

    accepted = evaluate_logistics_gate(
        family,
        baseline,
        instance_artifact=instance_path,
        result_artifact=result_path,
    )
    assert accepted.accepted is True
    assert accepted.gate_id == "WS-AUTONOMOUS-LOGISTICS-EXT-01"


def test_logistics_gate_requires_multiple_instances_and_degraded_case(tmp_path):
    instance_path = tmp_path / "instances.json"
    result_path = tmp_path / "baseline.json"
    instance_path.write_text("{}", encoding="utf-8")
    result_path.write_text("{}", encoding="utf-8")
    family = _family(instance_path)
    family = MissionInstanceFamilyRecord(**{**family.__dict__, "instance_count": 1, "disruption_scenario_count": 0})
    baseline = _baseline(family, result_path)
    baseline = ClassicalBaselineRecord(**{**baseline.__dict__, "instances_solved": 1, "feasible_instances": 1})

    decision = evaluate_logistics_gate(family, baseline, instance_artifact=instance_path, result_artifact=result_path)
    assert decision.accepted is False
    assert any("at least 3" in reason for reason in decision.reasons)
    assert any("disruption" in reason for reason in decision.reasons)


def test_classical_baseline_must_cover_full_family(tmp_path):
    instance_path = tmp_path / "instances.json"
    result_path = tmp_path / "baseline.json"
    instance_path.write_text("{}", encoding="utf-8")
    result_path.write_text("{}", encoding="utf-8")
    family = _family(instance_path)
    baseline = _baseline(family, result_path)
    baseline = ClassicalBaselineRecord(**{**baseline.__dict__, "instances_solved": 2, "feasible_instances": 2})

    decision = evaluate_logistics_gate(family, baseline, instance_artifact=instance_path, result_artifact=result_path)
    assert decision.accepted is False
    assert any("full frozen instance family" in reason for reason in decision.reasons)


def test_template_cannot_be_confused_with_toy_qaoa_evidence():
    payload = logistics_template_as_dict()
    assert payload["gate_id"] == "WS-AUTONOMOUS-LOGISTICS-EXT-01"
    assert "four-choice synthetic QAOA toy problem cannot satisfy" in payload["claim_control"]
