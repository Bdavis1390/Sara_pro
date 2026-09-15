from __future__ import annotations

import copy
import random
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from .rmabm import BLOCKED_ACTIONS, RMABMResult, run_synthetic_rmabm


FaultKind = Literal[
    "drop_observation",
    "delay_observation",
    "reduce_confidence",
    "duplicate_observation_id",
    "remove_human_authority",
    "request_blocked_action",
]


class FaultSpec(BaseModel):
    fault_id: str = Field(min_length=1)
    kind: FaultKind
    target_observation_id: str | None = None
    amount: float | None = None


class FaultRunResult(BaseModel):
    fault_id: str
    kind: FaultKind
    accepted: bool
    rejected_reason: str | None = None
    authorized_advisory_count: int = Field(ge=0)
    hold_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    stale_observation_ids: list[str] = Field(default_factory=list)
    audit_sha256: str | None = None
    boundary_integrity: bool


def build_seeded_fault_plan(fixture: dict[str, Any], *, seed: int) -> tuple[FaultSpec, ...]:
    """Build a reproducible synthetic fault campaign.

    Faults are limited to data-quality, provenance-lineage, human-authorization,
    and policy-boundary behavior. No engagement or fire-control logic is added.
    """
    observations = list(fixture.get("observations", []))
    observation_ids = sorted(str(item["observation_id"]) for item in observations)
    if not observation_ids:
        raise ValueError("fault campaign requires at least one synthetic observation")

    rng = random.Random(seed)
    delay_target = rng.choice(observation_ids)
    confidence_target = rng.choice(observation_ids)
    drop_target = rng.choice(observation_ids)
    duplicate_target = rng.choice(observation_ids)

    return (
        FaultSpec(fault_id="F01-DELAY", kind="delay_observation", target_observation_id=delay_target, amount=20.0),
        FaultSpec(
            fault_id="F02-CONFIDENCE",
            kind="reduce_confidence",
            target_observation_id=confidence_target,
            amount=0.10,
        ),
        FaultSpec(fault_id="F03-DROP", kind="drop_observation", target_observation_id=drop_target),
        FaultSpec(
            fault_id="F04-DUPLICATE-ID",
            kind="duplicate_observation_id",
            target_observation_id=duplicate_target,
        ),
        FaultSpec(fault_id="F05-NO-HUMAN", kind="remove_human_authority"),
        FaultSpec(fault_id="F06-BLOCKED-ACTION", kind="request_blocked_action"),
    )


def _find_observation(fixture: dict[str, Any], observation_id: str) -> dict[str, Any]:
    for observation in fixture.get("observations", []):
        if str(observation.get("observation_id")) == observation_id:
            return observation
    raise ValueError(f"unknown target_observation_id={observation_id!r}")


def apply_fault(fixture: dict[str, Any], fault: FaultSpec) -> dict[str, Any]:
    mutated = copy.deepcopy(fixture)
    mutated["scenario_id"] = f"{fixture['scenario_id']}::{fault.fault_id}"

    if fault.kind == "drop_observation":
        if not fault.target_observation_id:
            raise ValueError("drop_observation requires target_observation_id")
        before = len(mutated.get("observations", []))
        mutated["observations"] = [
            item
            for item in mutated.get("observations", [])
            if str(item.get("observation_id")) != fault.target_observation_id
        ]
        if len(mutated["observations"]) == before:
            raise ValueError(f"unknown target_observation_id={fault.target_observation_id!r}")

    elif fault.kind == "delay_observation":
        if not fault.target_observation_id or fault.amount is None:
            raise ValueError("delay_observation requires target_observation_id and amount")
        observation = _find_observation(mutated, fault.target_observation_id)
        observation["t_seconds"] = max(0.0, float(observation["t_seconds"]) - abs(float(fault.amount)))
        observation["source_status"] = "synthetic_fault_injected"

    elif fault.kind == "reduce_confidence":
        if not fault.target_observation_id or fault.amount is None:
            raise ValueError("reduce_confidence requires target_observation_id and amount")
        observation = _find_observation(mutated, fault.target_observation_id)
        observation["confidence"] = max(0.0, min(1.0, float(fault.amount)))
        observation["source_status"] = "synthetic_fault_injected"

    elif fault.kind == "duplicate_observation_id":
        if not fault.target_observation_id:
            raise ValueError("duplicate_observation_id requires target_observation_id")
        observation = copy.deepcopy(_find_observation(mutated, fault.target_observation_id))
        observation["sensor_id"] = f"{observation['sensor_id']}-DUP"
        observation["source_status"] = "synthetic_fault_injected"
        mutated.setdefault("observations", []).append(observation)

    elif fault.kind == "remove_human_authority":
        mutated["human_authority"] = None

    elif fault.kind == "request_blocked_action":
        mutated["requested_action"] = "fire_control_cue"

    else:  # pragma: no cover - pydantic constrains this
        raise ValueError(f"unsupported fault kind: {fault.kind}")

    return mutated


def _validate_unique_observation_ids(fixture: dict[str, Any]) -> None:
    ids = [str(item.get("observation_id")) for item in fixture.get("observations", [])]
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate observation ids rejected: {duplicates}")


def _boundary_integrity(result: RMABMResult) -> bool:
    allowed_decisions = {"AUTHORIZED_ADVISORY", "HOLD", "BLOCK"}
    if any(decision.decision not in allowed_decisions for decision in result.decisions):
        return False
    if any(
        decision.decision == "AUTHORIZED_ADVISORY" and decision.requested_action.strip().lower() in BLOCKED_ACTIONS
        for decision in result.decisions
    ):
        return False
    return True


def run_fault(fixture: dict[str, Any], fault: FaultSpec) -> FaultRunResult:
    mutated = apply_fault(fixture, fault)
    try:
        _validate_unique_observation_ids(mutated)
        result = run_synthetic_rmabm(mutated)
    except ValueError as exc:
        return FaultRunResult(
            fault_id=fault.fault_id,
            kind=fault.kind,
            accepted=False,
            rejected_reason=str(exc),
            authorized_advisory_count=0,
            hold_count=0,
            block_count=0,
            boundary_integrity=True,
        )

    counts = Counter(decision.decision for decision in result.decisions)
    return FaultRunResult(
        fault_id=fault.fault_id,
        kind=fault.kind,
        accepted=True,
        authorized_advisory_count=counts["AUTHORIZED_ADVISORY"],
        hold_count=counts["HOLD"],
        block_count=counts["BLOCK"],
        stale_observation_ids=result.stale_observation_ids,
        audit_sha256=result.audit_sha256,
        boundary_integrity=_boundary_integrity(result),
    )


def run_seeded_fault_campaign(fixture: dict[str, Any], *, seed: int) -> tuple[FaultRunResult, ...]:
    return tuple(run_fault(fixture, fault) for fault in build_seeded_fault_plan(fixture, seed=seed))
