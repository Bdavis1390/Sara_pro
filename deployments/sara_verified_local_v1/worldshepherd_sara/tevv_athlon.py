from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import canonical_digest


class TEVVStage(str, Enum):
    ARTICULATE_ORGANIZE = "Articulate & Organize"
    DEFINE_CONSTRUCT = "Define & Construct"
    APPLY_MEASURE = "Apply & Measure"
    SYNTHESIZE_INTERROGATE = "Synthesize & Interrogate"


class ToolCategory(str, Enum):
    MODEL_TESTING = "MODEL_TESTING"
    RED_TEAMING = "RED_TEAMING"
    FIELD_USER_TESTING = "FIELD_USER_TESTING"
    SIMULATION = "SIMULATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    OTHER = "OTHER"


class MetrologyBlock(BaseModel):
    block_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    evidence_required: list[str] = Field(min_length=1)
    trustworthiness_characteristics: list[str] = Field(default_factory=list)
    acceptance_rule: str | None = None


class TEVVTool(BaseModel):
    tool_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: ToolCategory
    description: str = Field(min_length=1)
    version_or_digest: str | None = None
    source_refs: list[str] = Field(default_factory=list)


class TEVVEvent(BaseModel):
    event_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    block_ids: list[str] = Field(min_length=1)
    tool_ids: list[str] = Field(min_length=1)
    expected_evidence: list[str] = Field(min_length=1)
    adversarial: bool = False
    physical_execution_required: bool = False


class TEVVAthlonPlan(BaseModel):
    schema: str = "ws-prime-tevv-athlon-plan-1"
    plan_id: str = Field(pattern=r"^WS-TEVV-[0-9a-f]{16}$")
    system_id: str = Field(min_length=1)
    evaluation_goal: str = Field(min_length=1)
    decision_use: str = Field(min_length=1)
    operational_context: str = Field(min_length=1)
    stakeholders: list[str] = Field(min_length=1)
    lifecycle_stages: list[str] = Field(min_length=1)
    system_attributes: list[str] = Field(min_length=1)
    blocks: list[MetrologyBlock] = Field(min_length=1)
    tools: list[TEVVTool] = Field(min_length=1)
    events: list[TEVVEvent] = Field(min_length=1)
    stage_order: list[TEVVStage] = Field(
        default_factory=lambda: [
            TEVVStage.ARTICULATE_ORGANIZE,
            TEVVStage.DEFINE_CONSTRUCT,
            TEVVStage.APPLY_MEASURE,
            TEVVStage.SYNTHESIZE_INTERROGATE,
        ]
    )
    reference_status: str = "NIST_AI_200_2_INITIAL_PUBLIC_DRAFT_AUGUST_2026"
    nist_conformance_claimed: bool = False
    nist_endorsement_claimed: bool = False
    certification_claimed: bool = False
    external_execution_authorized: bool = False
    physical_validation_claimed: bool = False

    @model_validator(mode="after")
    def validate_contract(self) -> "TEVVAthlonPlan":
        expected_stages = [
            TEVVStage.ARTICULATE_ORGANIZE,
            TEVVStage.DEFINE_CONSTRUCT,
            TEVVStage.APPLY_MEASURE,
            TEVVStage.SYNTHESIZE_INTERROGATE,
        ]
        if self.stage_order != expected_stages:
            raise ValueError("TEVV stage order must preserve the four-stage draft sequence")
        if self.nist_conformance_claimed or self.nist_endorsement_claimed or self.certification_claimed:
            raise ValueError("PRIME-TEVV may not self-claim NIST conformance, endorsement, or certification")
        if self.external_execution_authorized:
            raise ValueError("PRIME-TEVV planning may not self-authorize external execution")
        if self.physical_validation_claimed:
            raise ValueError("PRIME-TEVV planning may not self-claim physical validation")

        block_ids = [block.block_id for block in self.blocks]
        tool_ids = [tool.tool_id for tool in self.tools]
        event_ids = [event.event_id for event in self.events]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("duplicate Metrology Block IDs")
        if len(set(tool_ids)) != len(tool_ids):
            raise ValueError("duplicate Tool IDs")
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("duplicate Event IDs")

        known_blocks = set(block_ids)
        known_tools = set(tool_ids)
        covered_blocks: set[str] = set()
        for event in self.events:
            unknown_blocks = set(event.block_ids) - known_blocks
            unknown_tools = set(event.tool_ids) - known_tools
            if unknown_blocks:
                raise ValueError(f"event references unknown Blocks: {sorted(unknown_blocks)}")
            if unknown_tools:
                raise ValueError(f"event references unknown Tools: {sorted(unknown_tools)}")
            covered_blocks.update(event.block_ids)
        missing = known_blocks - covered_blocks
        if missing:
            raise ValueError(f"every Metrology Block requires at least one Event: {sorted(missing)}")
        return self


class TEVVMeasurement(BaseModel):
    measurement_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: Any
    units: str | None = None
    source_refs: list[str] = Field(min_length=1)
    uncertainty: Any | None = None
    passed_acceptance_rule: bool | None = None


class TEVVAthlonResult(BaseModel):
    schema: str = "ws-prime-tevv-athlon-result-1"
    plan_id: str = Field(pattern=r"^WS-TEVV-[0-9a-f]{16}$")
    plan_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    measurements: list[TEVVMeasurement] = Field(default_factory=list)
    synthesized_findings: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    decision: str = Field(min_length=1)
    external_execution_performed: bool = False
    physical_validation_claimed: bool = False
    nist_conformance_claimed: bool = False
    nist_endorsement_claimed: bool = False
    result_digest: str = ""

    @model_validator(mode="after")
    def fail_closed(self) -> "TEVVAthlonResult":
        if self.external_execution_performed:
            raise ValueError("TEVV result may not claim external execution without separate evidence")
        if self.physical_validation_claimed:
            raise ValueError("TEVV result may not self-claim physical validation")
        if self.nist_conformance_claimed or self.nist_endorsement_claimed:
            raise ValueError("TEVV result may not self-claim NIST conformance or endorsement")
        return self


def _plan_material(payload: dict[str, Any]) -> dict[str, Any]:
    material = dict(payload)
    material.pop("plan_id", None)
    return material


def make_tevv_plan(**kwargs: Any) -> TEVVAthlonPlan:
    provisional = {
        "plan_id": "WS-TEVV-0000000000000000",
        **kwargs,
    }
    validated = TEVVAthlonPlan.model_validate(provisional)
    material = _plan_material(validated.model_dump(mode="json"))
    plan_id = "WS-TEVV-" + canonical_digest(material).split(":", 1)[1][:16]
    return TEVVAthlonPlan.model_validate({**validated.model_dump(mode="json"), "plan_id": plan_id})


def plan_digest(plan: TEVVAthlonPlan) -> str:
    return canonical_digest(plan.model_dump(mode="json"))


def validate_measurements(plan: TEVVAthlonPlan, measurements: list[TEVVMeasurement]) -> None:
    events = {event.event_id: event for event in plan.events}
    blocks = {block.block_id for block in plan.blocks}
    tools = {tool.tool_id for tool in plan.tools}
    seen: set[str] = set()
    for measurement in measurements:
        if measurement.measurement_id in seen:
            raise ValueError(f"duplicate measurement ID: {measurement.measurement_id}")
        seen.add(measurement.measurement_id)
        if measurement.event_id not in events:
            raise ValueError(f"measurement references unknown Event: {measurement.event_id}")
        if measurement.block_id not in blocks:
            raise ValueError(f"measurement references unknown Block: {measurement.block_id}")
        if measurement.tool_id not in tools:
            raise ValueError(f"measurement references unknown Tool: {measurement.tool_id}")
        event = events[measurement.event_id]
        if measurement.block_id not in event.block_ids:
            raise ValueError("measurement Block is not assigned to its Event")
        if measurement.tool_id not in event.tool_ids:
            raise ValueError("measurement Tool is not assigned to its Event")


def make_tevv_result(
    plan: TEVVAthlonPlan,
    *,
    measurements: list[TEVVMeasurement],
    synthesized_findings: list[str],
    unresolved_questions: list[str],
    decision: str,
) -> TEVVAthlonResult:
    validate_measurements(plan, measurements)
    payload = {
        "plan_id": plan.plan_id,
        "plan_digest": plan_digest(plan),
        "measurements": [item.model_dump(mode="json") for item in measurements],
        "synthesized_findings": synthesized_findings,
        "unresolved_questions": unresolved_questions,
        "decision": decision,
        "external_execution_performed": False,
        "physical_validation_claimed": False,
        "nist_conformance_claimed": False,
        "nist_endorsement_claimed": False,
    }
    material = {"schema": "ws-prime-tevv-athlon-result-1", **payload, "result_digest": ""}
    digest_material = dict(material)
    digest_material.pop("result_digest")
    return TEVVAthlonResult.model_validate(
        {**material, "result_digest": canonical_digest(digest_material)}
    )


def verify_result_digest(result: TEVVAthlonResult) -> bool:
    payload = result.model_dump(mode="json")
    claimed = payload.pop("result_digest")
    return claimed == canonical_digest(payload)
