from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SourceStatus(str, Enum):
    OFFICIAL_SOURCE_VERIFIED = "OFFICIAL_SOURCE_VERIFIED"
    GOVERNMENT_SECONDARY_VERIFIED = "GOVERNMENT_SECONDARY_VERIFIED"
    PRIMARY_TECHNICAL_SOURCE = "PRIMARY_TECHNICAL_SOURCE"
    THIRD_PARTY_DISCOVERY_ONLY = "THIRD_PARTY_DISCOVERY_ONLY"
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
    UNVERIFIED = "UNVERIFIED"


class CapabilityStatus(str, Enum):
    PROVEN_INTERNALLY = "PROVEN_INTERNALLY"
    IMPLEMENTED_IN_SOFTWARE = "IMPLEMENTED_IN_SOFTWARE"
    SUPPORTED_BY_LITERATURE = "SUPPORTED_BY_LITERATURE"
    SIMULATED_ONLY = "SIMULATED_ONLY"
    HYPOTHESIS = "HYPOTHESIS"
    SPECULATIVE_EXTENSION = "SPECULATIVE_EXTENSION"
    REQUIRES_LAB_VALIDATION = "REQUIRES_LAB_VALIDATION"
    REQUIRES_PARTNER_VALIDATION = "REQUIRES_PARTNER_VALIDATION"
    REQUIRES_LEGAL_REVIEW = "REQUIRES_LEGAL_REVIEW"
    NOT_CURRENTLY_CLAIMED = "NOT_CURRENTLY_CLAIMED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DemandClass(str, Enum):
    CONFIRMED_DEMAND = "CONFIRMED_DEMAND"
    EMERGING_DEMAND = "EMERGING_DEMAND"
    WORLDSHEPHERD_FORECAST = "WORLDSHEPHERD_FORECAST"


class ForecastHorizon(str, Enum):
    D0_90 = "0-90D"
    M3_12 = "3-12M"
    M12_24_PLUS = "12-24M_PLUS"


class EvidenceScope(str, Enum):
    SOFTWARE = "SOFTWARE"
    SIMULATION = "SIMULATION"
    PHYSICAL = "PHYSICAL"
    ADMINISTRATIVE = "ADMINISTRATIVE"


class ResultStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class ReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class SupersessionState(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class SourceRecord(BaseModel):
    title: str = Field(min_length=1)
    agency: str = Field(min_length=1)
    url: str = Field(min_length=1)
    solicitation_or_topic: str | None = None
    source_status: SourceStatus
    retrieved_utc: str


class RequirementDeltaRecord(BaseModel):
    requirement_delta_id: str = Field(pattern=r"^PRE-RD-[0-9]{4}-[0-9]{4,}$")
    demand_class: DemandClass
    source: SourceRecord
    statement: str = Field(min_length=1)
    recurrence: str = Field(min_length=1)
    forecast_horizon: ForecastHorizon
    affected_lanes: list[str] = Field(default_factory=list)
    existing_capability: list[str] = Field(default_factory=list)
    capability_status: list[CapabilityStatus] = Field(default_factory=list)
    missing_capability: list[str] = Field(default_factory=list)
    experiment_or_demonstration_needed: list[str] = Field(default_factory=list)
    partner_needed: list[str] = Field(default_factory=list)
    evidence_target: list[str] = Field(default_factory=list)
    likely_future_programs: list[str] = Field(default_factory=list)
    claims_boundary: list[str] = Field(default_factory=list)

    def capture_ready(self) -> bool:
        return self.source.source_status not in {
            SourceStatus.UNVERIFIED,
            SourceStatus.THIRD_PARTY_DISCOVERY_ONLY,
            SourceStatus.CONFLICTING_SOURCES,
        }


class EvidenceGraphNode(BaseModel):
    node_id: str = Field(min_length=1)
    node_type: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_ref: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(BaseModel):
    edge_id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    source_ref: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraph(BaseModel):
    graph_id: str = Field(min_length=1)
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def edges_reference_known_nodes(self) -> "EvidenceGraph":
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError(f"edge {edge.edge_id} references unknown node")
        return self


class ReviewRecord(BaseModel):
    status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewer: str | None = None
    reviewed_utc: str | None = None


class SupersessionRecord(BaseModel):
    state: SupersessionState = SupersessionState.CURRENT
    superseded_by: str | None = None


class QualificationEvidenceRecord(BaseModel):
    qualification_id: str = Field(pattern=r"^WS-QE-[0-9]{4}-[0-9]{4,}$")
    requirement_id: str = Field(min_length=1)
    test_id: str = Field(min_length=1)
    evidence_scope: EvidenceScope
    capability_status: CapabilityStatus
    environment_digest: str = Field(min_length=1)
    configuration_digest: str = Field(min_length=1)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: list[dict[str, Any]] = Field(default_factory=list)
    result: ResultStatus
    rationale: str = Field(min_length=1)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    software_commit: str | None = None
    executed_utc: str
    operator: str = Field(min_length=1)
    physical_validation_performed: bool = False
    review: ReviewRecord = Field(default_factory=ReviewRecord)
    supersession: SupersessionRecord = Field(default_factory=SupersessionRecord)

    @model_validator(mode="after")
    def prevent_unvalidated_physical_proof(self) -> "QualificationEvidenceRecord":
        if (
            self.evidence_scope == EvidenceScope.PHYSICAL
            and self.capability_status == CapabilityStatus.PROVEN_INTERNALLY
            and not self.physical_validation_performed
        ):
            raise ValueError(
                "physical PROVEN_INTERNALLY status requires physical validation evidence"
            )
        return self


def canonical_digest(value: BaseModel | dict[str, Any] | list[Any]) -> str:
    if isinstance(value, BaseModel):
        payload: Any = value.model_dump(mode="json")
    else:
        payload = value
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def compile_qualification_bundle(
    requirement: RequirementDeltaRecord,
    evidence: list[QualificationEvidenceRecord],
    graph: EvidenceGraph | None = None,
) -> dict[str, Any]:
    records = [item.model_dump(mode="json") for item in evidence]
    bundle = {
        "requirement": requirement.model_dump(mode="json"),
        "evidence": records,
        "evidence_graph": graph.model_dump(mode="json") if graph else None,
        "capture_ready_source": requirement.capture_ready(),
        "claims_boundary": requirement.claims_boundary,
    }
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
