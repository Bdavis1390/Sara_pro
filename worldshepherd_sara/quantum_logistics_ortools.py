"""Strong classical CP-SAT comparator for frozen logistics assignment families.

The solver capability is useful before quantum/annealing comparison, but a controlled
fixture is not mission evidence. WS-AUTONOMOUS-LOGISTICS-EXT-01 remains open until
an actual mission-relevant family is frozen, solved in full, reviewed, and retained.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Mapping

from ortools.sat.python import cp_model


def _digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CPSATInstanceResult:
    instance_id: str
    status: str
    optimal: bool
    feasible: bool
    objective_value: float | None
    best_objective_bound: float | None
    assignments: tuple[tuple[str, str], ...]
    wall_time_seconds: float
    conflicts: int
    branches: int
    result_digest: str


@dataclass(frozen=True)
class CPSATFamilyResult:
    fixture_or_family_id: str
    instance_kind: str
    solver_name: str
    solver_version: str
    solver_class: str
    deterministic_worker_count: int
    random_seed: int
    time_limit_seconds_per_instance: float
    instance_count: int
    feasible_instances: int
    optimal_instances: int
    all_instances_feasible: bool
    all_instances_optimal: bool
    source_artifact_digest: str
    configuration_digest: str
    result_digest: str
    results: tuple[CPSATInstanceResult, ...]
    claim_control: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def solve_assignment_instance(
    instance: Mapping[str, Any],
    *,
    time_limit_seconds: float = 30.0,
    random_seed: int = 9675,
) -> CPSATInstanceResult:
    instance_id = str(instance.get("instance_id", "")).strip()
    if not instance_id:
        raise ValueError("instance_id is required")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")

    vehicles_raw = instance.get("vehicles")
    tasks_raw = instance.get("tasks")
    if not isinstance(vehicles_raw, list) or not vehicles_raw:
        raise ValueError("vehicles must be a non-empty list")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ValueError("tasks must be a non-empty list")

    vehicles: dict[str, int] = {}
    unavailable: set[str] = set()
    for row in vehicles_raw:
        if not isinstance(row, Mapping):
            raise ValueError("each vehicle must be an object")
        vid = str(row.get("vehicle_id", "")).strip()
        if not vid or vid in vehicles:
            raise ValueError("vehicle_id values must be unique and non-empty")
        vehicles[vid] = _positive_int(row.get("capacity"), f"capacity for {vid}")
        if row.get("available", True) is False:
            unavailable.add(vid)

    task_rows: list[tuple[str, int, dict[str, int]]] = []
    seen_tasks: set[str] = set()
    for row in tasks_raw:
        if not isinstance(row, Mapping):
            raise ValueError("each task must be an object")
        tid = str(row.get("task_id", "")).strip()
        if not tid or tid in seen_tasks:
            raise ValueError("task_id values must be unique and non-empty")
        seen_tasks.add(tid)
        demand = _positive_int(row.get("demand"), f"demand for {tid}")
        costs_raw = row.get("cost_by_vehicle")
        if not isinstance(costs_raw, Mapping) or not costs_raw:
            raise ValueError(f"cost_by_vehicle for {tid} must be a non-empty object")
        costs: dict[str, int] = {}
        for vehicle_id, raw_cost in costs_raw.items():
            vehicle_id = str(vehicle_id)
            if vehicle_id not in vehicles:
                raise ValueError(f"task {tid} references unknown vehicle {vehicle_id}")
            if isinstance(raw_cost, bool) or not isinstance(raw_cost, int) or raw_cost < 0:
                raise ValueError(f"cost for {tid}/{vehicle_id} must be a non-negative integer")
            costs[vehicle_id] = int(raw_cost)
        if not any(v not in unavailable for v in costs):
            raise ValueError(f"task {tid} has no available assignment")
        task_rows.append((tid, demand, costs))

    model = cp_model.CpModel()
    x: dict[tuple[str, str], Any] = {}
    for tid, _, costs in task_rows:
        for vid in costs:
            if vid not in unavailable:
                x[(tid, vid)] = model.new_bool_var(f"assign__{tid}__{vid}")

    for tid, _, costs in task_rows:
        vars_for_task = [x[(tid, vid)] for vid in costs if (tid, vid) in x]
        model.add(sum(vars_for_task) == 1)

    for vid, capacity in vehicles.items():
        if vid in unavailable:
            continue
        terms = []
        for tid, demand, costs in task_rows:
            if vid in costs and (tid, vid) in x:
                terms.append(demand * x[(tid, vid)])
        if terms:
            model.add(sum(terms) <= capacity)

    objective_terms = []
    for tid, _, costs in task_rows:
        for vid, cost in costs.items():
            if (tid, vid) in x:
                objective_terms.append(cost * x[(tid, vid)])
    model.minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_seconds)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = int(random_seed)
    status_code = solver.solve(model)
    status = solver.status_name(status_code)
    feasible = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    optimal = status_code == cp_model.OPTIMAL

    assignments: list[tuple[str, str]] = []
    if feasible:
        for (tid, vid), var in sorted(x.items()):
            if solver.value(var):
                assignments.append((tid, vid))
    objective = float(solver.objective_value) if feasible else None
    best_bound = float(solver.best_objective_bound) if feasible else None
    payload = {
        "instance_id": instance_id,
        "status": status,
        "optimal": optimal,
        "feasible": feasible,
        "objective_value": objective,
        "best_objective_bound": best_bound,
        "assignments": assignments,
        "wall_time_seconds": float(solver.wall_time),
        "conflicts": int(solver.num_conflicts),
        "branches": int(solver.num_branches),
    }
    return CPSATInstanceResult(result_digest=_digest(payload), **payload)


def solve_family_mapping(
    family: Mapping[str, Any],
    *,
    source_artifact_digest: str,
    time_limit_seconds_per_instance: float = 30.0,
    random_seed: int = 9675,
) -> CPSATFamilyResult:
    family_id = str(family.get("fixture_id") or family.get("family_id") or "").strip()
    instance_kind = str(family.get("instance_kind", "unspecified")).strip()
    instances = family.get("instances")
    if not family_id:
        raise ValueError("fixture_id or family_id is required")
    if not isinstance(instances, list) or len(instances) < 1:
        raise ValueError("instances must be a non-empty list")
    results = tuple(
        solve_assignment_instance(row, time_limit_seconds=time_limit_seconds_per_instance, random_seed=random_seed)
        for row in instances
    )
    version = importlib.metadata.version("ortools")
    config = {
        "solver": "Google OR-Tools CP-SAT",
        "solver_version": version,
        "workers": 1,
        "random_seed": random_seed,
        "time_limit_seconds_per_instance": time_limit_seconds_per_instance,
        "objective_sense": "minimize",
        "model": "binary task-to-vehicle assignment with integer capacity constraints",
    }
    body = {
        "fixture_or_family_id": family_id,
        "instance_kind": instance_kind,
        "source_artifact_digest": source_artifact_digest,
        "configuration_digest": _digest(config),
        "results": [asdict(row) for row in results],
    }
    feasible_count = sum(row.feasible for row in results)
    optimal_count = sum(row.optimal for row in results)
    return CPSATFamilyResult(
        fixture_or_family_id=family_id,
        instance_kind=instance_kind,
        solver_name="Google OR-Tools CP-SAT",
        solver_version=version,
        solver_class="integer constraint programming / CP-SAT",
        deterministic_worker_count=1,
        random_seed=random_seed,
        time_limit_seconds_per_instance=float(time_limit_seconds_per_instance),
        instance_count=len(results),
        feasible_instances=feasible_count,
        optimal_instances=optimal_count,
        all_instances_feasible=feasible_count == len(results),
        all_instances_optimal=optimal_count == len(results),
        source_artifact_digest=source_artifact_digest,
        configuration_digest=_digest(config),
        result_digest=_digest(body),
        results=results,
        claim_control=(
            "Strong classical comparator result only. Controlled fixtures validate solver capability but cannot satisfy "
            "WS-AUTONOMOUS-LOGISTICS-EXT-01. A mission gate requires an independently justified mission-relevant family, "
            "full-family execution, retained artifacts, and technical review."
        ),
    )


def solve_family_file(
    path: str | Path,
    *,
    time_limit_seconds_per_instance: float = 30.0,
    random_seed: int = 9675,
) -> CPSATFamilyResult:
    source = Path(path).read_bytes()
    payload = json.loads(source.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("family artifact must contain a JSON object")
    return solve_family_mapping(
        payload,
        source_artifact_digest="sha256:" + sha256(source).hexdigest(),
        time_limit_seconds_per_instance=time_limit_seconds_per_instance,
        random_seed=random_seed,
    )
