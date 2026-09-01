from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import (
    CapabilityStatus,
    DemandClass,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceScope,
    ForecastHorizon,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    SourceRecord,
    SourceStatus,
    canonical_digest,
    compile_qualification_bundle,
)


class GeoReviewState(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    HUMAN_REVIEW_COMPLETED = "HUMAN_REVIEW_COMPLETED"


class EnvironmentalSourceRecord(BaseModel):
    source_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    dataset_type: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    spatial_resolution: str = Field(min_length=1)
    temporal_resolution: str = Field(min_length=1)
    coverage_area: str = Field(min_length=1)
    license_terms: str = Field(min_length=1)
    retrieval_time_utc: str = Field(min_length=1)
    retrieval_hash: str = Field(min_length=1)
    confidence_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_hashed_retrieval(self) -> "EnvironmentalSourceRecord":
        if not self.retrieval_hash.startswith("sha256:"):
            raise ValueError("environmental source retrieval_hash must be sha256-prefixed")
        return self


class ChangeDetectionEvidence(BaseModel):
    event_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    baseline_period: str = Field(min_length=1)
    comparison_period: str = Field(min_length=1)
    target_geometry: str = Field(min_length=1)
    change_type: str = Field(min_length=1)
    area_estimate: str = Field(min_length=1)
    severity_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    uncertainty_reason: str = Field(min_length=1)
    method: str = Field(min_length=1)
    configuration_hash: str = Field(min_length=1)
    result_hash: str = Field(min_length=1)
    null_control_passed: bool
    review_state: GeoReviewState = GeoReviewState.UNREVIEWED
    human_review_rationale: str | None = None

    @model_validator(mode="after")
    def enforce_uncertainty_and_hashes(self) -> "ChangeDetectionEvidence":
        for field_name in ("configuration_hash", "result_hash"):
            if not getattr(self, field_name).startswith("sha256:"):
                raise ValueError(f"{field_name} must be sha256-prefixed")
        if self.confidence_score < 0.95 and not self.uncertainty_reason.strip():
            raise ValueError("non-perfect confidence requires an uncertainty reason")
        if self.review_state == GeoReviewState.HUMAN_REVIEW_COMPLETED and not self.human_review_rationale:
            raise ValueError("completed human review requires a rationale")
        return self


class BAEGeoEvidenceOverlay(BaseModel):
    bae_signal_id: str = Field(min_length=1)
    bae_lane: list[str] = Field(default_factory=list)
    worldshepherd_asset: list[str] = Field(default_factory=list)
    maturity_label: str = Field(min_length=1)
    missing_validation: list[str] = Field(default_factory=list)
    proposed_demo: str = Field(min_length=1)
    likely_bae_value: str = Field(min_length=1)
    strongest_bae_pathway: list[str] = Field(default_factory=list)
    supplier_readiness_dependency: list[str] = Field(default_factory=list)
    claim_boundary: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def block_false_partner_claims(self) -> "BAEGeoEvidenceOverlay":
        prohibited = ("BAE_VALIDATED", "BAE_CERTIFIED", "BAE_APPROVED", "CMMC_CERTIFIED")
        text = " ".join(
            [self.maturity_label, self.proposed_demo, self.likely_bae_value]
            + self.claim_boundary
        ).upper()
        if any(term in text for term in prohibited):
            raise ValueError("BAE overlay cannot assert validation, approval, certification, or adoption")
        return self


def build_environmental_baseline_requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0020",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(
            title="Environmental baseline and geospatial provenance readiness",
            agency="Worldshepherd PRE",
            url="internal://pre/environmental-baseline-018",
            solicitation_or_topic="WS-GEO-PROV-001",
            source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE,
            retrieved_utc="2026-09-01T15:00:00Z",
        ),
        statement=(
            "Environmental, infrastructure, and mission-context systems need auditable "
            "geospatial baselines, repeatable change detection, uncertainty handling, "
            "null controls, and human-reviewed response decisions."
        ),
        recurrence=(
            "Recurring across wildfire, drought, land restoration, water security, "
            "environmental compliance, infrastructure resilience, distributed sensing, and mission planning."
        ),
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=[
            "SARA evidence orchestration",
            "ECHO SENTINEL LINK provenance",
            "PRIME SENTINEL authorization",
            "OVERWATCH geospatial COP",
            "autonomous sensing/control",
            "distributed sensing",
            "BAE mission engineering readiness",
        ],
        existing_capability=[
            "bounded internal software evidence for audit/provenance workflows",
            "claims-control separation between prediction, simulation, and validation",
        ],
        capability_status=[
            CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
            CapabilityStatus.SIMULATED_ONLY,
            CapabilityStatus.REQUIRES_PARTNER_VALIDATION,
        ],
        missing_capability=[
            "field-calibrated geospatial pipeline",
            "independent replay by an external reviewer",
            "signed evidence bundle",
            "ground-truth linkage and measurement-uncertainty evidence",
        ],
        experiment_or_demonstration_needed=[
            "WS-GEO-PROV-001A public-dataset replay with null control and degraded-data case"
        ],
        partner_needed=[
            "geospatial analyst",
            "environmental scientist or field-data partner",
            "independent reviewer/lab for external replay",
        ],
        evidence_target=[
            "dataset version and retrieval hash",
            "processing configuration hash",
            "change-detection result hash",
            "null-control result",
            "uncertainty reason",
            "human review decision",
            "SARA audit chain",
            "sanitized BAE overlay",
        ],
        likely_future_programs=[
            "DOE and national-lab environmental sensing",
            "critical infrastructure resilience",
            "distributed sensing and mission engineering",
            "BAE RIVETS/ADAPT/ADAMS-style screening",
        ],
        claims_boundary=[
            "Prediction schedules preparation only and never upgrades capability maturity.",
            "This record does not establish land-restoration performance, emergency-response authority, BAE validation, DOE validation, CMMC/NIST conformity, or hardware field performance.",
            "Internal software evidence remains INTERNAL_UNSIGNED unless a later record documents external signing or independent reproduction.",
        ],
    )


def build_geo_prov_bundle(
    *, software_commit: str, executed_utc: str, operator: str
) -> dict[str, Any]:
    requirement = build_environmental_baseline_requirement()
    source = EnvironmentalSourceRecord(
        source_id="ENV-SRC-WS-GEO-PROV-001A",
        provider="public geospatial dataset placeholder",
        dataset_name="bounded land/water/fire change fixture",
        dataset_type="raster/vector/time_series",
        dataset_version="synthetic-fixture-v1",
        spatial_resolution="scenario-defined",
        temporal_resolution="scenario-defined",
        coverage_area="bounded public demonstration region",
        license_terms="public/non-sensitive fixture for internal replay",
        retrieval_time_utc=executed_utc,
        retrieval_hash=canonical_digest({"fixture": "WS-GEO-PROV-001A", "version": "synthetic-fixture-v1"}),
        confidence_notes=[
            "Synthetic fixture proves evidence handling only.",
            "No physical environmental performance is inferred.",
        ],
    )
    change = ChangeDetectionEvidence(
        event_id="ENV-CHANGE-WS-GEO-PROV-001A",
        source_id=source.source_id,
        baseline_period="baseline-window-synthetic",
        comparison_period="comparison-window-synthetic",
        target_geometry="POLYGON_PLACEHOLDER_PUBLIC_REGION",
        change_type="land_water_fire_context_change",
        area_estimate="scenario-defined",
        severity_score=0.5,
        confidence_score=0.82,
        uncertainty_reason="Synthetic replay includes degraded-data and source-disagreement controls.",
        method="deterministic fixture evaluation with null-control and human-review gate",
        configuration_hash=canonical_digest({"method": "WS-GEO-PROV-001A", "null_control": True}),
        result_hash=canonical_digest({"event": "ENV-CHANGE-WS-GEO-PROV-001A", "result": "PASS"}),
        null_control_passed=True,
        review_state=GeoReviewState.HUMAN_REVIEW_COMPLETED,
        human_review_rationale="Accepted for internal evidence-chain demonstration only.",
    )
    bae_overlay = BAEGeoEvidenceOverlay(
        bae_signal_id="PRE-BAE-GEOSPATIAL-PROVENANCE-019",
        bae_lane=[
            "C5ISR",
            "distributed sensing",
            "mission engineering",
            "digital engineering",
            "resilient infrastructure",
        ],
        worldshepherd_asset=["SARA", "ECHO SENTINEL LINK", "PRIME SENTINEL", "OVERWATCH"],
        maturity_label="INTERNAL SOFTWARE EVIDENCE / DESIGN-SPEC READY / REQUIRES EXTERNAL VALIDATION",
        missing_validation=[
            "independent replay",
            "signed evidence bundle",
            "field-calibrated data",
            "BAE-specific integration test",
            "CMMC/NIST/DFARS control evidence",
        ],
        proposed_demo=(
            "Mission-context environmental disruption scenario with degraded data, source disagreement, "
            "human review, replay manifest, and sanitized evidence bundle."
        ),
        likely_bae_value=(
            "Demonstrates provenance discipline for heterogeneous sensing and uncertain mission-state evidence "
            "without claiming BAE adoption or operational validation."
        ),
        strongest_bae_pathway=["RIVETS", "ADAPT/ADAMS", "Virtual Proving Ground-style plugfest", "Mission Advantage screening"],
        supplier_readiness_dependency=[
            "SBOM/build provenance",
            "threat model",
            "CUI/CDI boundary statement",
            "NIST SP 800-171/CMMC/DFARS gap map",
            "data-rights/IP markings",
        ],
        claim_boundary=[
            "No BAE interest, adoption, endorsement, certification, classified access, or partnership is inferred.",
            "No supplier cybersecurity conformity is claimed without documentary evidence.",
        ],
    )
    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-0020",
        requirement_id=requirement.requirement_delta_id,
        test_id="WS-GEO-PROV-001A",
        evidence_scope=EvidenceScope.SIMULATION,
        capability_status=CapabilityStatus.SIMULATED_ONLY,
        environment_digest=canonical_digest({"execution_context": "geo_provenance_bundle", "operator": operator}),
        configuration_digest=change.configuration_hash,
        inputs=[source.model_dump(mode="json")],
        outputs=[change.model_dump(mode="json"), bae_overlay.model_dump(mode="json")],
        metrics=[
            {"name": "null_control_passed", "value": change.null_control_passed},
            {"name": "confidence_score", "value": change.confidence_score},
        ],
        uncertainty=[{"reason": change.uncertainty_reason, "scope": "synthetic_replay"}],
        result=ResultStatus.PASS,
        rationale="Synthetic replay record satisfies schema/provenance gates only.",
        negative_evidence=[
            {"case": "field_validation", "result": "NOT_PERFORMED"},
            {"case": "external_reproduction", "result": "NOT_PERFORMED"},
            {"case": "BAE_validation", "result": "NOT_PERFORMED"},
        ],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
        physical_validation_performed=False,
    )
    graph = EvidenceGraph(
        graph_id="WS-GEO-PROV-001A-GRAPH",
        nodes=[
            EvidenceGraphNode(node_id="source", node_type="dataset", label=source.dataset_name, confidence=0.82),
            EvidenceGraphNode(node_id="change", node_type="change_event", label=change.change_type, confidence=0.82),
            EvidenceGraphNode(node_id="review", node_type="human_review", label=change.review_state.value, confidence=1.0),
            EvidenceGraphNode(node_id="bae", node_type="partner_readiness_overlay", label=bae_overlay.bae_signal_id, confidence=0.6),
        ],
        edges=[
            EvidenceGraphEdge(edge_id="e1", source_node_id="source", target_node_id="change", relation="feeds"),
            EvidenceGraphEdge(edge_id="e2", source_node_id="change", target_node_id="review", relation="requires_human_review"),
            EvidenceGraphEdge(edge_id="e3", source_node_id="review", target_node_id="bae", relation="sanitized_for_screening_overlay"),
        ],
    )
    bundle = compile_qualification_bundle(requirement, [evidence], graph)
    bundle["geo_provenance"] = {
        "environmental_source": source.model_dump(mode="json"),
        "change_event": change.model_dump(mode="json"),
    }
    bundle["bae_evidence_overlay"] = bae_overlay.model_dump(mode="json")
    bundle["claims_boundary"].extend(bae_overlay.claim_boundary)
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
