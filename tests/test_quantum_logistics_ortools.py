import json
from pathlib import Path

import pytest
pytest.importorskip("ortools")

from worldshepherd_sara.quantum_logistics_ortools import solve_assignment_instance, solve_family_file


def test_controlled_family_is_solved_by_strong_classical_comparator():
    result = solve_family_file("benchmarks/quantum/logistics_cp_sat_fixture.json", time_limit_seconds_per_instance=10.0)
    assert result.solver_version == "9.15.6755"
    assert result.instance_count == 3
    assert result.feasible_instances == 3
    assert result.optimal_instances == 3
    assert result.all_instances_optimal is True
    assert result.result_digest.startswith("sha256:")
    assert result.instance_kind == "controlled_software_fixture_not_mission_evidence"
    degraded = next(row for row in result.results if row.instance_id == "degraded-v2-unavailable")
    assert all(vehicle != "v2" for _, vehicle in degraded.assignments)


def test_rejects_fractional_costs_because_cp_sat_contract_is_integer():
    instance = {
        "instance_id": "bad-float",
        "vehicles": [{"vehicle_id": "v1", "capacity": 2}],
        "tasks": [{"task_id": "t1", "demand": 1, "cost_by_vehicle": {"v1": 1.5}}],
    }
    with pytest.raises(ValueError, match="non-negative integer"):
        solve_assignment_instance(instance)


def test_fixture_explicitly_cannot_be_treated_as_mission_evidence():
    payload = json.loads(Path("benchmarks/quantum/logistics_cp_sat_fixture.json").read_text())
    assert payload["instance_kind"] == "controlled_software_fixture_not_mission_evidence"
    assert "cannot satisfy WS-AUTONOMOUS-LOGISTICS-EXT-01" in payload["claim_control"]
