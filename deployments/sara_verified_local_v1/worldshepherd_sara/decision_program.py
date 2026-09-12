from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .prime import ActionProposal


CLAIMS_BOUNDARY = "SIMULATED_ONLY / INTERNAL SOFTWARE DEMONSTRATOR"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Direction(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class ConstraintOperator(str, Enum):
    LE = "<="
    GE = ">="


class AssumptionStatus(str, Enum):
    VALIDATED = "VALIDATED"
    UNVALIDATED = "UNVALIDATED"
    CONTRADICTED = "CONTRADICTED"


class BiasCheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class PackageState(str, Enum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    BLOCKED = "BLOCKED"


class Objective(FrozenModel):
    objective_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    direction: Direction
    unit: str = Field(min_length=1)
    weight: float = Field(gt=0, allow_inf_nan=False)


class Option(FrozenModel):
    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class Constraint(FrozenModel):
    constraint_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    operator: ConstraintOperator
    threshold: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class Assumption(FrozenModel):
    assumption_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    status: AssumptionStatus
    source_ref: str = Field(min_length=1)


class Risk(FrozenModel):
    risk_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    impact: float = Field(ge=0, le=1, allow_inf_nan=False)
    penalty_weight: float = Field(ge=0, le=1, default=0.0, allow_inf_nan=False)
    option_id: str | None = None
    source_ref: str = Field(min_length=1)


class BiasCheck(FrozenModel):
    bias_check_id: str = Field(min_length=1)
    check: str = Field(min_length=1)
    status: BiasCheckStatus
    evidence_ref: str = Field(min_length=1)


class EvidenceDatum(FrozenModel):
    evidence_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)


class DecisionEpoch(FrozenModel):
    epoch_id: str = Field(min_length=1)
    evaluated_utc: str = Field(min_length=1)
    evidence: tuple[EvidenceDatum, ...] = Field(min_length=1)
    change_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def unique_evidence_keys(self) -> "DecisionEpoch":
        keys: set[tuple[str, str]] = set()
        ids: set[str] = set()
        for datum in self.evidence:
            if datum.evidence_id in ids:
                raise ValueError(f"duplicate evidence_id: {datum.evidence_id}")
            ids.add(datum.evidence_id)
            key = (datum.option_id, datum.metric_id)
            if key in keys:
                raise ValueError(f"duplicate option/metric evidence: {key}")
            keys.add(key)
        return self


class DecisionSpec(FrozenModel):
    program_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    objectives: tuple[Objective, ...] = Field(min_length=1)
    options: tuple[Option, ...] = Field(min_length=2)
    constraints: tuple[Constraint, ...] = Field(default_factory=tuple)
    assumptions: tuple[Assumption, ...] = Field(min_length=1)
    risks: tuple[Risk, ...] = Field(min_length=1)
    bias_checks: tuple[BiasCheck, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_schema(self) -> "DecisionSpec":
        def unique(values: list[str], label: str) -> None:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")

        unique([o.objective_id for o in self.objectives], "objective_id")
        unique([o.option_id for o in self.options], "option_id")
        unique([c.constraint_id for c in self.constraints], "constraint_id")
        unique([a.assumption_id for a in self.assumptions], "assumption_id")
        unique([r.risk_id for r in self.risks], "risk_id")
        unique([b.bias_check_id for b in self.bias_checks], "bias_check_id")

        option_ids = {o.option_id for o in self.options}
        for risk in self.risks:
            if risk.option_id is not None and risk.option_id not in option_ids:
                raise ValueError(f"risk references unknown option: {risk.option_id}")

        metric_units: dict[str, str] = {}
        for objective in self.objectives:
            existing = metric_units.setdefault(objective.metric_id, objective.unit)
            if existing != objective.unit:
                raise ValueError(
                    f"conflicting canonical units for {objective.metric_id}: {existing} vs {objective.unit}"
                )
        for constraint in self.constraints:
            existing = metric_units.setdefault(constraint.metric_id, constraint.unit)
            if existing != constraint.unit:
                raise ValueError(
                    f"conflicting canonical units for {constraint.metric_id}: {existing} vs {constraint.unit}"
                )
        return self


class ObjectiveContribution(FrozenModel):
    objective_id: str
    metric_id: str
    raw_value: float = Field(allow_inf_nan=False)
    normalized_value: float = Field(allow_inf_nan=False)
    weighted_contribution: float = Field(allow_inf_nan=False)


class OptionEvaluation(FrozenModel):
    option_id: str
    feasible: bool
    failed_constraints: tuple[str, ...] = Field(default_factory=tuple)
    objective_contributions: tuple[ObjectiveContribution, ...] = Field(default_factory=tuple)
    base_score: float = Field(default=0.0, allow_inf_nan=False)
    risk_penalty: float = Field(default=0.0, allow_inf_nan=False)
    final_score: float = Field(default=0.0, allow_inf_nan=False)


class FlipCondition(FrozenModel):
    objective_id: str
    metric_id: str
    direction: Direction
    normalized_shift_required: float = Field(allow_inf_nan=False)
    explanation: str


class GovernedAgentStep(FrozenModel):
    proposal_id: str
    action: str
    rationale: tuple[str, ...]
    authority_required: str
    state: str


class DecisionPackage(FrozenModel):
    program_id: str
    version: int = Field(ge=1)
    epoch_id: str
    evaluated_utc: str
    change_reason: str
    spec_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_state: PackageState
    recommended_option_id: str | None
    runner_up_option_id: str | None
    option_evaluations: tuple[OptionEvaluation, ...]
    flip_conditions: tuple[FlipCondition, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    agentic_plan: tuple[GovernedAgentStep, ...]
    parent_package_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    human_signoff: bool = False
    claims_boundary: str = CLAIMS_BOUNDARY

    @model_validator(mode="after")
    def verify_declared_hash(self) -> "DecisionPackage":
        payload = self.model_dump(mode="json", exclude={"package_hash"})
        expected = _sha256(payload)
        if self.package_hash != expected:
            raise ValueError("DecisionPackage package_hash does not match its contents")
        return self


class DecisionHistory(FrozenModel):
    program_id: str
    packages: tuple[DecisionPackage, ...]

    @model_validator(mode="after")
    def verify_chain(self) -> "DecisionHistory":
        previous_hash: str | None = None
        for expected_version, package in enumerate(self.packages, start=1):
            # Pydantic model_copy(update=...) intentionally does not revalidate the
            # copied model. Recompute the hash at the custody boundary so even an
            # unchecked/stale nested DecisionPackage cannot enter a valid history.
            package_payload = package.model_dump(mode="json", exclude={"package_hash"})
            expected_package_hash = _sha256(package_payload)
            if package.package_hash != expected_package_hash:
                raise ValueError("DecisionHistory package_hash does not match package contents")
            if package.program_id != self.program_id:
                raise ValueError("DecisionHistory package program_id mismatch")
            if package.version != expected_version:
                raise ValueError("DecisionHistory versions must be contiguous starting at 1")
            if package.parent_package_hash != previous_hash:
                raise ValueError("DecisionHistory parent_package_hash chain mismatch")
            previous_hash = package.package_hash
        return self


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def build_governed_agent_plan(program_id: str) -> tuple[GovernedAgentStep, ...]:
    actions = (
        ("validate_decision_schema", "Validate objectives, options, constraints, assumptions, risks, and bias checks."),
        ("collect_bounded_evidence", "Collect only evidence bound to declared options and metrics."),
        ("evaluate_declared_options", "Run the deterministic declared-option evaluation."),
        ("analyze_decision_flip", "Compute bounded sensitivity conditions that could change the recommendation."),
        ("prepare_decision_package", "Assemble a provenance-bearing package for identified-human review."),
    )
    steps: list[GovernedAgentStep] = []
    for index, (action, rationale) in enumerate(actions, start=1):
        proposal = ActionProposal(
            proposal_id=f"{program_id}-STEP-{index:02d}",
            action=action,
            rationale=[rationale],
            authority_required="identified-human-authority",
        )
        steps.append(
            GovernedAgentStep(
                proposal_id=proposal.proposal_id,
                action=proposal.action,
                rationale=tuple(proposal.rationale),
                authority_required=proposal.authority_required,
                state=proposal.state.value,
            )
        )
    return tuple(steps)


def _canonical_metric_units(spec: DecisionSpec) -> dict[str, str]:
    units = {objective.metric_id: objective.unit for objective in spec.objectives}
    for constraint in spec.constraints:
        units.setdefault(constraint.metric_id, constraint.unit)
    return units


def _evidence_index(spec: DecisionSpec, epoch: DecisionEpoch) -> dict[tuple[str, str], EvidenceDatum]:
    option_ids = {option.option_id for option in spec.options}
    canonical_units = _canonical_metric_units(spec)
    index: dict[tuple[str, str], EvidenceDatum] = {}
    for datum in epoch.evidence:
        if datum.option_id not in option_ids:
            raise ValueError(f"evidence references unknown option: {datum.option_id}")
        if datum.metric_id not in canonical_units:
            raise ValueError(f"evidence references undeclared metric: {datum.metric_id}")
        required_unit = canonical_units[datum.metric_id]
        if datum.unit != required_unit:
            raise ValueError(
                f"unit mismatch for {datum.metric_id}: expected {required_unit}, received {datum.unit}"
            )
        index[(datum.option_id, datum.metric_id)] = datum

    required_metrics = set(canonical_units)
    for option_id in option_ids:
        missing = [metric for metric in sorted(required_metrics) if (option_id, metric) not in index]
        if missing:
            raise ValueError(f"missing evidence for {option_id}: {', '.join(missing)}")
    return index


def _constraint_failures(
    spec: DecisionSpec,
    option_id: str,
    evidence: dict[tuple[str, str], EvidenceDatum],
) -> tuple[str, ...]:
    failures: list[str] = []
    for constraint in spec.constraints:
        value = evidence[(option_id, constraint.metric_id)].value
        passed = (
            value <= constraint.threshold
            if constraint.operator == ConstraintOperator.LE
            else value >= constraint.threshold
        )
        if not passed:
            failures.append(constraint.constraint_id)
    return tuple(sorted(failures))


def _normalized(
    *,
    value: float,
    low: float,
    high: float,
    direction: Direction,
) -> float:
    if high == low:
        return 1.0
    raw = (value - low) / (high - low)
    return raw if direction == Direction.MAXIMIZE else 1.0 - raw


def evaluate_decision(
    spec: DecisionSpec,
    epoch: DecisionEpoch,
    *,
    version: int = 1,
    parent_package_hash: str | None = None,
) -> DecisionPackage:
    evidence = _evidence_index(spec, epoch)
    evaluation_parts: dict[str, dict[str, Any]] = {}

    spec_hash = _sha256(spec.model_dump(mode="json"))
    evidence_payload = {
        "epoch_id": epoch.epoch_id,
        "evaluated_utc": epoch.evaluated_utc,
        "change_reason": epoch.change_reason,
        "evidence": [
            item.model_dump(mode="json")
            for item in sorted(epoch.evidence, key=lambda datum: datum.evidence_id)
        ],
    }
    evidence_hash = _sha256(evidence_payload)

    feasible_ids: list[str] = []
    for option in spec.options:
        failures = _constraint_failures(spec, option.option_id, evidence)
        feasible = not failures
        if feasible:
            feasible_ids.append(option.option_id)
        evaluation_parts[option.option_id] = {
            "feasible": feasible,
            "failed_constraints": failures,
            "objective_contributions": [],
            "base_score": 0.0,
            "risk_penalty": 0.0,
            "final_score": 0.0,
        }

    blockers: list[str] = []
    warnings: list[str] = []
    if not feasible_ids:
        blockers.append("NO_FEASIBLE_OPTION")

    total_weight = sum(objective.weight for objective in spec.objectives)
    if feasible_ids:
        for objective in spec.objectives:
            values = [evidence[(option_id, objective.metric_id)].value for option_id in feasible_ids]
            low, high = min(values), max(values)
            for option_id in feasible_ids:
                datum = evidence[(option_id, objective.metric_id)]
                normalized = _normalized(
                    value=datum.value,
                    low=low,
                    high=high,
                    direction=objective.direction,
                )
                contribution = normalized * (objective.weight / total_weight)
                evaluation_parts[option_id]["objective_contributions"].append(
                    ObjectiveContribution(
                        objective_id=objective.objective_id,
                        metric_id=objective.metric_id,
                        raw_value=datum.value,
                        normalized_value=normalized,
                        weighted_contribution=contribution,
                    )
                )

        for option_id in feasible_ids:
            parts = evaluation_parts[option_id]
            base_score = sum(item.weighted_contribution for item in parts["objective_contributions"])
            risk_penalty = sum(
                risk.probability * risk.impact * risk.penalty_weight
                for risk in spec.risks
                if risk.option_id == option_id
            )
            parts["base_score"] = round(base_score, 12)
            parts["risk_penalty"] = round(risk_penalty, 12)
            parts["final_score"] = round(max(0.0, base_score - risk_penalty), 12)

    evaluations = tuple(
        OptionEvaluation(
            option_id=option_id,
            feasible=parts["feasible"],
            failed_constraints=parts["failed_constraints"],
            objective_contributions=tuple(parts["objective_contributions"]),
            base_score=parts["base_score"],
            risk_penalty=parts["risk_penalty"],
            final_score=parts["final_score"],
        )
        for option_id, parts in sorted(evaluation_parts.items())
    )
    evaluation_by_id = {item.option_id: item for item in evaluations}

    contradicted = sorted(
        assumption.assumption_id
        for assumption in spec.assumptions
        if assumption.status == AssumptionStatus.CONTRADICTED
    )
    unvalidated = sorted(
        assumption.assumption_id
        for assumption in spec.assumptions
        if assumption.status == AssumptionStatus.UNVALIDATED
    )
    bias_failures = sorted(
        check.bias_check_id for check in spec.bias_checks if check.status == BiasCheckStatus.FAIL
    )
    bias_warnings = sorted(
        check.bias_check_id for check in spec.bias_checks if check.status == BiasCheckStatus.WARN
    )

    blockers.extend(f"CONTRADICTED_ASSUMPTION:{item}" for item in contradicted)
    blockers.extend(f"BIAS_CHECK_FAILED:{item}" for item in bias_failures)
    warnings.extend(f"UNVALIDATED_ASSUMPTION:{item}" for item in unvalidated)
    warnings.extend(f"BIAS_CHECK_WARNING:{item}" for item in bias_warnings)

    ranked = sorted(
        (item for item in evaluations if item.feasible),
        key=lambda item: (-item.final_score, item.option_id),
    )
    recommended = ranked[0].option_id if ranked else None
    runner_up = ranked[1].option_id if len(ranked) > 1 else None

    flip_conditions: list[FlipCondition] = []
    if recommended is not None and runner_up is not None:
        margin = evaluation_by_id[recommended].final_score - evaluation_by_id[runner_up].final_score
        winner_by_objective = {
            item.objective_id: item
            for item in evaluation_by_id[recommended].objective_contributions
        }
        for objective in spec.objectives:
            normalized_shift = margin / (objective.weight / total_weight)
            flip_conditions.append(
                FlipCondition(
                    objective_id=objective.objective_id,
                    metric_id=objective.metric_id,
                    direction=objective.direction,
                    normalized_shift_required=round(max(0.0, normalized_shift), 12),
                    explanation=(
                        f"A normalized disadvantage of more than {normalized_shift:.6f} on "
                        f"{objective.objective_id}, absent offsetting changes, is sufficient to erase "
                        f"the current {margin:.6f} aggregate-score margin. Current winner contribution="
                        f"{winner_by_objective[objective.objective_id].weighted_contribution:.6f}."
                    ),
                )
            )

    state = PackageState.BLOCKED if blockers else PackageState.READY_FOR_HUMAN_REVIEW
    payload = {
        "program_id": spec.program_id,
        "version": version,
        "epoch_id": epoch.epoch_id,
        "evaluated_utc": epoch.evaluated_utc,
        "change_reason": epoch.change_reason,
        "spec_hash": spec_hash,
        "evidence_hash": evidence_hash,
        "package_state": state.value,
        "recommended_option_id": recommended,
        "runner_up_option_id": runner_up,
        "option_evaluations": [item.model_dump(mode="json") for item in evaluations],
        "flip_conditions": [item.model_dump(mode="json") for item in flip_conditions],
        "blockers": sorted(blockers),
        "warnings": sorted(warnings),
        "agentic_plan": [item.model_dump(mode="json") for item in build_governed_agent_plan(spec.program_id)],
        "parent_package_hash": parent_package_hash,
        "human_signoff": False,
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    package_hash = _sha256(payload)
    return DecisionPackage(package_hash=package_hash, **payload)


def refresh_decision_program(spec: DecisionSpec, epochs: list[DecisionEpoch]) -> DecisionHistory:
    if not epochs:
        raise ValueError("at least one decision epoch is required")
    packages: list[DecisionPackage] = []
    parent: str | None = None
    for version, epoch in enumerate(epochs, start=1):
        package = evaluate_decision(
            spec,
            epoch,
            version=version,
            parent_package_hash=parent,
        )
        packages.append(package)
        parent = package.package_hash
    return DecisionHistory(program_id=spec.program_id, packages=tuple(packages))