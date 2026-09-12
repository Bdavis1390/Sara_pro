from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from .improvement_feedback import feedback_cursor_digest
from .improvement_runtime import ImprovementRuntime, ImprovementRuntimeError
from .qualification import canonical_digest


EVIDENCE_MANIFEST_SCHEMA = "ws-ri-evidence-manifest-1"


class ImprovementEvidenceManifest(BaseModel):
    schema: str = EVIDENCE_MANIFEST_SCHEMA
    generated_utc: str = Field(min_length=1)
    record_count: int = Field(ge=0)
    head_sequence: int | None = None
    head_record_digest: str | None = None
    state_counts: dict[str, int]
    record_digests: list[str]
    records_digest: str = Field(min_length=1)
    feedback_cursor: dict[str, Any]
    feedback_cursor_digest: str = Field(min_length=1)
    ledger_chain_verified: bool
    claim_promotion_performed: bool = False
    deployment_performed: bool = False
    external_execution_performed: bool = False
    claims_boundary: str = Field(min_length=1)
    manifest_digest: str = Field(min_length=1)


def _manifest_material(runtime: ImprovementRuntime, *, generated_utc: str) -> dict[str, object]:
    if not generated_utc.strip():
        raise ImprovementRuntimeError("generated_utc is required")
    if not runtime.ledger.verify_chain():
        raise ImprovementRuntimeError("WS-RI ledger chain verification failed")
    records = runtime.ledger.records()
    cursor = runtime.load_cursor()
    record_digests = [record.record_digest for record in records]
    return {
        "schema": EVIDENCE_MANIFEST_SCHEMA,
        "generated_utc": generated_utc.strip(),
        "record_count": len(records),
        "head_sequence": None if not records else records[-1].sequence,
        "head_record_digest": None if not records else records[-1].record_digest,
        "state_counts": dict(sorted(Counter(record.state for record in records).items())),
        "record_digests": record_digests,
        "records_digest": canonical_digest({"record_digests": record_digests}),
        "feedback_cursor": cursor.model_dump(mode="json"),
        "feedback_cursor_digest": feedback_cursor_digest(cursor),
        "ledger_chain_verified": True,
        "claim_promotion_performed": False,
        "deployment_performed": False,
        "external_execution_performed": False,
        "claims_boundary": (
            "deterministic local evidence manifest only; it does not establish external retention, "
            "qualification, deployment authorization, certification, or signed ECHO inclusion"
        ),
    }


def build_evidence_manifest(
    runtime: ImprovementRuntime,
    *,
    generated_utc: str,
) -> ImprovementEvidenceManifest:
    material = _manifest_material(runtime, generated_utc=generated_utc)
    return ImprovementEvidenceManifest(
        **material,
        manifest_digest=canonical_digest(material),
    )


def verify_evidence_manifest(manifest: ImprovementEvidenceManifest) -> bool:
    material = manifest.model_dump(mode="json")
    observed = str(material.pop("manifest_digest"))
    if observed != canonical_digest(material):
        return False
    record_digests = material.get("record_digests")
    if not isinstance(record_digests, list):
        return False
    if material.get("records_digest") != canonical_digest({"record_digests": record_digests}):
        return False
    cursor = material.get("feedback_cursor")
    if not isinstance(cursor, dict):
        return False
    try:
        from .improvement_feedback import ImprovementFeedbackCursor

        parsed = ImprovementFeedbackCursor.model_validate(cursor)
    except ValueError:
        return False
    return material.get("feedback_cursor_digest") == feedback_cursor_digest(parsed)


def manifest_matches_runtime(
    manifest: ImprovementEvidenceManifest,
    runtime: ImprovementRuntime,
) -> bool:
    if not verify_evidence_manifest(manifest):
        return False
    records = runtime.ledger.records()
    cursor = runtime.load_cursor()
    if not runtime.ledger.verify_chain():
        return False
    return (
        manifest.record_count == len(records)
        and manifest.head_sequence == (None if not records else records[-1].sequence)
        and manifest.head_record_digest == (None if not records else records[-1].record_digest)
        and manifest.record_digests == [record.record_digest for record in records]
        and manifest.feedback_cursor_digest == feedback_cursor_digest(cursor)
    )
