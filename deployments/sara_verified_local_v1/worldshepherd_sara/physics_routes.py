from __future__ import annotations

from collections import Counter
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from .anomalous_force_analysis import (
    AnomalousForceEvidenceSummary,
    assess_anomalous_force_summary,
)
from .auth import Role, require_admin, resolve_role
from .claims_linter_physics import lint_physics_claim
from .external_lab_evidence import (
    ExternalLaboratoryEvidencePackage,
    assess_lab_package,
)
from .models import AuditRecord
from .physics_storage import PhysicsEvidenceStore
from .physics_validation import (
    EvidenceScore,
    PhysicsVerificationRecord,
    ValidationState,
    apply_hard_gates,
)

router = APIRouter(tags=["physics-validation"])


class PhysicsClaimLintRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    record: PhysicsVerificationRecord | None = None


class PhysicsEvidenceEvaluationRequest(BaseModel):
    record: PhysicsVerificationRecord
    score: EvidenceScore


def _physics_store() -> PhysicsEvidenceStore:
    return PhysicsEvidenceStore()


def _provenance_audit_fields(record: PhysicsVerificationRecord) -> dict[str, Any]:
    experiment = record.experiment
    provenance = experiment.provenance if experiment is not None else None
    return {
        "claim_label": record.claim_label,
        "claim_class": record.claim_class,
        "approval_state": record.cre1aws_approval_state.value,
        "evidence_package_refs": sorted(record.evidence_package_refs),
        "raw_data_digests": sorted(experiment.raw_data_digests) if experiment else [],
        "calibration_record_ids": (
            sorted(experiment.calibration_record_ids) if experiment else []
        ),
        "source_manifest_digest": (
            provenance.source_manifest_digest if provenance else None
        ),
        "configuration_digest": (
            provenance.configuration_digest if provenance else None
        ),
        "acquisition_time_utc": (
            provenance.acquisition_time_utc if provenance else None
        ),
        "time_reference": provenance.time_reference if provenance else None,
        "coordinate_frame": provenance.coordinate_frame if provenance else None,
    }


@router.get("/v1/physics/status")
def physics_status(
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    evidence_store = _physics_store()
    ok, detail = evidence_store.check_storage()
    return {
        "ok": ok,
        "storage": detail,
        "status": evidence_store.status(),
    }


@router.get("/v1/physics/records")
def physics_records(
    role: Annotated[Role, Depends(resolve_role)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    project_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    artifact_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> dict[str, object]:
    require_admin(role)
    records = _physics_store().read_recent(
        limit=limit,
        project_id=project_id,
        artifact_id=artifact_id,
    )
    return {"records": [record.model_dump(mode="json") for record in records]}


@router.get("/v1/physics/metrics")
def physics_metrics(
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    """OVERWATCH-ready validation/provenance counters from the local PVK store."""
    require_admin(role)
    records = _physics_store().read_recent(limit=500)
    validation_states = Counter(record.validation_state.value for record in records)
    replication_states = Counter(
        record.experiment.replication_state.value
        for record in records
        if record.experiment is not None
    )
    convergence_states = Counter(
        record.simulation.convergence_status.value
        for record in records
        if record.simulation is not None
    )
    physical_records = [
        record
        for record in records
        if record.validation_state
        in {
            ValidationState.INTERNAL_TEST,
            ValidationState.INDEPENDENTLY_REPLICATED,
            ValidationState.QUALIFIED,
            ValidationState.CERTIFIED,
        }
    ]
    return {
        "records_considered": len(records),
        "validation_states": dict(sorted(validation_states.items())),
        "replication_states": dict(sorted(replication_states.items())),
        "convergence_states": dict(sorted(convergence_states.items())),
        "quality_gates": {
            "physical_records": len(physical_records),
            "missing_provenance": sum(
                1
                for record in physical_records
                if record.experiment is None or record.experiment.provenance is None
            ),
            "missing_calibration": sum(
                1
                for record in physical_records
                if record.experiment is not None
                and record.experiment.measurement_equipment_used
                and not record.experiment.calibration_record_ids
            ),
            "failed_or_partial_convergence": sum(
                1
                for record in records
                if record.simulation is not None
                and record.simulation.convergence_status.value in {"failed", "partial"}
            ),
            "pending_independent_review": sum(
                1
                for record in records
                if record.independent_review_state.value in {"requested", "in_progress"}
            ),
            "p4_records": sum(
                1 for record in records if record.physics_layer.value == "P4_BEYOND_STANDARD_MODEL"
            ),
        },
    }


@router.post("/admin/physics/lab-packages/validate")
def physics_lab_package_validate(
    body: ExternalLaboratoryEvidencePackage,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    """Validate external-lab evidence structure; never promotes physics maturity."""
    require_admin(role)
    result = assess_lab_package(body)
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_lab_package_validated",
            actor=role.value,
            payload={
                "package_id": body.package_id,
                "campaign_id": body.campaign_id,
                "project_id": body.project_id,
                "artifact_id": body.artifact_id,
                "laboratory_organization": body.laboratory_organization,
                "facility": body.facility,
                "independence": body.independence.value,
                "package_digest": result["package_digest"],
                "evidence_complete": result["evidence_complete"],
                "blockers": result["blockers"],
                "warnings": result["warnings"],
                "maturity_promoted": False,
            },
        )
    )
    return result


@router.post("/admin/physics/anomalous-force/assess")
def physics_anomalous_force_assess(
    body: AnomalousForceEvidenceSummary,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    """Apply AF-0..AF-7 interpretation gates; never confirms extraordinary physics."""
    require_admin(role)
    result = assess_anomalous_force_summary(body)
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_anomalous_force_assessed",
            actor=role.value,
            payload={
                "campaign_id": body.campaign_id,
                "article_id": body.article_id,
                "preregistered": body.preregistered,
                "classification": result["classification"],
                "photon_ratio_abs": result["photon_ratio_abs"],
                "conservative_residual_lower_bound_n": result[
                    "conservative_residual_lower_bound_n"
                ],
                "failed_gates": result["failed_gates"],
                "open_gates": result["open_gates"],
                "bounded_effect_claim_candidate": result[
                    "bounded_effect_claim_candidate"
                ],
                "reactionless_claim_allowed": False,
                "electrogravitic_claim_allowed": False,
                "new_physics_confirmed": False,
            },
        )
    )
    return result


@router.post("/admin/physics/records")
def physics_record_append(
    body: PhysicsVerificationRecord,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    _physics_store().append(body)
    payload = {
        "record_id": body.record_id,
        "artifact_id": body.artifact_id,
        "project_id": body.project_id,
        "physics_layer": body.physics_layer.value,
        "validation_state": body.validation_state.value,
        **_provenance_audit_fields(body),
    }
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_record_appended",
            actor=role.value,
            payload=payload,
        )
    )
    return {
        "accepted": True,
        "record": body.model_dump(mode="json"),
    }


@router.post("/admin/physics/lint")
def physics_claim_lint(
    body: PhysicsClaimLintRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    findings = lint_physics_claim(body.text, record=body.record)
    blocked = any(item.severity.value == "BLOCK" for item in findings)
    record_fields: dict[str, Any] = {}
    if body.record is not None:
        record_fields = {
            "record_id": body.record.record_id,
            "artifact_id": body.record.artifact_id,
            "project_id": body.record.project_id,
            "validation_state": body.record.validation_state.value,
            **_provenance_audit_fields(body.record),
        }
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_claim_linted",
            actor=role.value,
            payload={
                **record_fields,
                "finding_count": len(findings),
                "blocked": blocked,
                "rule_ids": sorted({item.rule_id for item in findings}),
            },
        )
    )
    return {
        "blocked": blocked,
        "findings": [item.model_dump(mode="json") for item in findings],
    }


@router.post("/admin/physics/evaluate")
def physics_evaluate(
    body: PhysicsEvidenceEvaluationRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    result = apply_hard_gates(record=body.record, score=body.score)
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_evidence_evaluated",
            actor=role.value,
            payload={
                "record_id": body.record.record_id,
                "artifact_id": body.record.artifact_id,
                "project_id": body.record.project_id,
                "validation_state": body.record.validation_state.value,
                **_provenance_audit_fields(body.record),
                "weighted_score": result["weighted_score"],
                "raw_classification": result["raw_classification"],
                "hard_gate_blocks": result["hard_gate_blocks"],
                "external_claim_allowed": result["external_claim_allowed"],
            },
        )
    )
    return result
