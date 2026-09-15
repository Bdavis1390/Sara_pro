"""Mission-instance and classical-baseline gate for WS-AUTONOMOUS-LOGISTICS.

Toy QUBO instances are useful software tests but cannot satisfy the calibrated mission
model gate. This module requires a retained mission-instance family, explicit objective
and constraints, disruption/degraded cases, and a strong classical reference result
before a quantum challenger may be compared on the same frozen problem family.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Mapping


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER = ("placeholder", "todo", "tbd", "unknown", "replace-me", "<", ">")


@dataclass(frozen=True)
class MissionInstanceFamilyRecord:
    project_id: str
    family_id: str
    mission_source: str
    mission_scope: str
    instance_count: int
    vehicle_count_range: tuple[int, int]
    task_count_range: tuple[int, int]
    objective_definition: str
    constraint_definition: str
    objective_digest: str
    constraint_digest: str
    instance_family_digest: str
    raw_instance_artifact_digest: str
    units_definition: str
    latency_budget_seconds: float
    degraded_state_definition: str
    disruption_scenario_count: int
    data_rights_or_provenance: str
    claim_control: str = (
        "Mission-instance family only. Acceptance establishes that the benchmark is sufficiently specified and provenance-controlled "
        "for comparative optimization; it does not prove mission performance or quantum advantage."
    )


@dataclass(frozen=True)
class ClassicalBaselineRecord:
    project_id: str
    family_id: str
    instance_family_digest: str
    solver_name: str
    solver_version: str
    solver_class: str
    configuration_digest: str
    result_digest: str
    result_artifact_digest: str
    instances_solved: int
    feasible_instances: int
    optimality_or_gap_definition: str
    objective_summary: str
    wall_time_seconds: float
    hardware_description: str
    test_protocol_digest: str
    claim_control: str = (
        "Classical reference only. Solver success/failure defines the comparator state for the frozen family and is not a deployment claim."
    )


@dataclass(frozen=True)
class LogisticsGateDecision:
    accepted: bool
    reasons: tuple[str, ...]
    gate_id: str = "WS-AUTONOMOUS-LOGISTICS-EXT-01"
    claim_control: str = (
        "Accepted means a mission-relevant instance family and strong classical baseline are structurally ready for comparison. "
        "It does not promote readiness unless the family is actually mission-relevant and passes separate technical review."
    )


def artifact_digest(path: str | Path) -> str:
    return "sha256:" + sha256(Path(path).read_bytes()).hexdigest()


def _is_sha(value: str) -> bool:
    return bool(_SHA256.fullmatch(value.strip().lower()))


def _placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(token in lowered for token in _PLACEHOLDER)


def validate_mission_instance_family(
    family: MissionInstanceFamilyRecord,
    *,
    instance_artifact: str | Path | None = None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if family.project_id != "WS-AUTONOMOUS-LOGISTICS":
        reasons.append("project_id must be WS-AUTONOMOUS-LOGISTICS")
    for field in ("family_id", "mission_source", "mission_scope", "objective_definition", "constraint_definition", "units_definition", "degraded_state_definition", "data_rights_or_provenance"):
        if _placeholder(str(getattr(family, field))):
            reasons.append(f"{field} must be concrete and non-placeholder")
    for field in ("objective_digest", "constraint_digest", "instance_family_digest", "raw_instance_artifact_digest"):
        if not _is_sha(str(getattr(family, field))):
            reasons.append(f"{field} must be a sha256 digest")
    if family.instance_count < 3:
        reasons.append("mission instance family must contain at least 3 instances")
    for label, limits in (("vehicle", family.vehicle_count_range), ("task", family.task_count_range)):
        if len(limits) != 2 or limits[0] <= 0 or limits[1] < limits[0]:
            reasons.append(f"{label}_count_range must be positive ordered bounds")
    if family.latency_budget_seconds <= 0:
        reasons.append("latency_budget_seconds must be positive")
    if family.disruption_scenario_count < 1:
        reasons.append("at least one degraded/disruption scenario is required")
    if instance_artifact is None:
        reasons.append("actual mission-instance artifact is required")
    else:
        path = Path(instance_artifact)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append("mission-instance artifact must exist and be non-empty")
        elif artifact_digest(path).lower() != family.raw_instance_artifact_digest.lower():
            reasons.append("mission-instance artifact digest mismatch")
    return tuple(reasons)


def validate_classical_baseline(
    baseline: ClassicalBaselineRecord,
    *,
    family: MissionInstanceFamilyRecord,
    result_artifact: str | Path | None = None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if baseline.project_id != family.project_id:
        reasons.append("baseline project_id mismatch")
    if baseline.family_id != family.family_id:
        reasons.append("baseline family_id mismatch")
    if baseline.instance_family_digest.lower() != family.instance_family_digest.lower():
        reasons.append("baseline is not bound to frozen instance family digest")
    for field in ("solver_name", "solver_version", "solver_class", "optimality_or_gap_definition", "objective_summary", "hardware_description"):
        if _placeholder(str(getattr(baseline, field))):
            reasons.append(f"{field} must be concrete and non-placeholder")
    for field in ("configuration_digest", "result_digest", "result_artifact_digest", "test_protocol_digest", "instance_family_digest"):
        if not _is_sha(str(getattr(baseline, field))):
            reasons.append(f"{field} must be a sha256 digest")
    if baseline.instances_solved != family.instance_count:
        reasons.append("classical baseline must attempt the full frozen instance family")
    if not 0 <= baseline.feasible_instances <= baseline.instances_solved:
        reasons.append("feasible_instances must be within attempted instance count")
    if baseline.wall_time_seconds <= 0:
        reasons.append("wall_time_seconds must be positive")
    if result_artifact is None:
        reasons.append("actual classical baseline result artifact is required")
    else:
        path = Path(result_artifact)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append("classical baseline result artifact must exist and be non-empty")
        elif artifact_digest(path).lower() != baseline.result_artifact_digest.lower():
            reasons.append("classical baseline result artifact digest mismatch")
    return tuple(reasons)


def evaluate_logistics_gate(
    family: MissionInstanceFamilyRecord,
    baseline: ClassicalBaselineRecord,
    *,
    instance_artifact: str | Path | None = None,
    result_artifact: str | Path | None = None,
) -> LogisticsGateDecision:
    reasons = list(validate_mission_instance_family(family, instance_artifact=instance_artifact))
    reasons.extend(validate_classical_baseline(baseline, family=family, result_artifact=result_artifact))
    return LogisticsGateDecision(accepted=not reasons, reasons=tuple(reasons))


def logistics_template_as_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "gate_id": "WS-AUTONOMOUS-LOGISTICS-EXT-01",
        "mission_instance_family": {
            "project_id": "WS-AUTONOMOUS-LOGISTICS",
            "family_id": "<replace-me>",
            "mission_source": "<actual source / exercise / partner / governed synthetic mission source>",
            "mission_scope": "<replace-me>",
            "instance_count": "<>=3>",
            "vehicle_count_range": ["<min>", "<max>"],
            "task_count_range": ["<min>", "<max>"],
            "objective_definition": "<replace-me>",
            "constraint_definition": "<replace-me>",
            "objective_digest": "<sha256>",
            "constraint_digest": "<sha256>",
            "instance_family_digest": "<sha256>",
            "raw_instance_artifact_digest": "<sha256>",
            "units_definition": "<replace-me>",
            "latency_budget_seconds": "<positive>",
            "degraded_state_definition": "<replace-me>",
            "disruption_scenario_count": "<>=1>",
            "data_rights_or_provenance": "<replace-me>"
        },
        "classical_baseline": {
            "solver_name": "<CP-SAT/MILP/other strong solver>",
            "solver_version": "<replace-me>",
            "solver_class": "<replace-me>",
            "configuration_digest": "<sha256>",
            "result_digest": "<sha256>",
            "result_artifact_digest": "<sha256>",
            "instances_solved": "<must equal instance_count>",
            "feasible_instances": "<0..instance_count>",
            "optimality_or_gap_definition": "<replace-me>",
            "objective_summary": "<replace-me>",
            "wall_time_seconds": "<positive>",
            "hardware_description": "<replace-me>",
            "test_protocol_digest": "<sha256>"
        },
        "claim_control": "Template only. The existing four-choice synthetic QAOA toy problem cannot satisfy this mission-instance gate."
    }
