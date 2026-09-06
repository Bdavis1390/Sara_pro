from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from .auth import Role, require_admin, resolve_role
from .claims_linter_physics import lint_physics_claim
from .models import AuditRecord
from .physics_storage import PhysicsEvidenceStore
from .physics_validation import (
    EvidenceScore,
    PhysicsVerificationRecord,
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


@router.post("/admin/physics/records")
def physics_record_append(
    body: PhysicsVerificationRecord,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    _physics_store().append(body)
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_record_appended",
            actor=role.value,
            payload={
                "record_id": body.record_id,
                "artifact_id": body.artifact_id,
                "project_id": body.project_id,
                "physics_layer": body.physics_layer.value,
                "validation_state": body.validation_state.value,
                "claim_class": body.claim_class,
            },
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
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="physics_claim_linted",
            actor=role.value,
            payload={
                "record_id": body.record.record_id if body.record else None,
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
                "project_id": body.record.project_id,
                "weighted_score": result["weighted_score"],
                "raw_classification": result["raw_classification"],
                "hard_gate_blocks": result["hard_gate_blocks"],
                "external_claim_allowed": result["external_claim_allowed"],
            },
        )
    )
    return result
