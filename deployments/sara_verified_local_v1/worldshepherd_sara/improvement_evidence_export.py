from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .improvement_feedback import ImprovementFeedbackCursor, feedback_cursor_digest
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

    @model_validator(mode="after")
    def fail_closed_and_consistent(self) -> "ImprovementEvidenceManifest":
        if not self.ledger_chain_verified:
            raise ValueError("evidence manifest requires a verified WS-RI ledger chain")
        if any(
            (
                self.claim_promotion_performed,
                self.deployment_performed,
                self.external_execution_performed,
            )
        ):
            raise ValueError("evidence manifest cannot claim promotion, deployment, or execution")
        if self.record_count != len(self.record_digests):
            raise ValueError("record_count must match record_digests")
        if sum(self.state_counts.values()) != self.record_count:
            raise ValueError("state_counts must sum to record_count")
        if any(value < 0 for value in self.state_counts.values()):
            raise ValueError("state_counts may not contain negative values")
        if self.record_count == 0:
            if self.head_sequence is not None or self.head_record_digest is not None:
                raise ValueError("empty manifest may not declare a ledger head")
        else:
            if self.head_sequence != self.record_count:
                raise ValueError("head_sequence must equal record_count for contiguous ledger export")
            if self.head_record_digest != self.record_digests[-1]:
                raise ValueError("head_record_digest must match final record digest")
        return self


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
    state_counts = material.get("state_counts")
    if not isinstance(record_digests, list) or not isinstance(state_counts, dict):
        return False
    record_count = material.get("record_count")
    if not isinstance(record_count, int) or record_count != len(record_digests):
        return False
    if any(not isinstance(value, int) or value < 0 for value in state_counts.values()):
        return False
    if sum(state_counts.values()) != record_count:
        return False
    if not material.get("ledger_chain_verified"):
        return False
    if any(
        bool(material.get(key))
        for key in (
            "claim_promotion_performed",
            "deployment_performed",
            "external_execution_performed",
        )
    ):
        return False
    if record_count == 0:
        if material.get("head_sequence") is not None or material.get("head_record_digest") is not None:
            return False
    else:
        if material.get("head_sequence") != record_count:
            return False
        if material.get("head_record_digest") != record_digests[-1]:
            return False
    if material.get("records_digest") != canonical_digest({"record_digests": record_digests}):
        return False
    cursor = material.get("feedback_cursor")
    if not isinstance(cursor, dict):
        return False
    try:
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
    expected_counts = dict(sorted(Counter(record.state for record in records).items()))
    return (
        manifest.record_count == len(records)
        and manifest.head_sequence == (None if not records else records[-1].sequence)
        and manifest.head_record_digest == (None if not records else records[-1].record_digest)
        and manifest.state_counts == expected_counts
        and manifest.record_digests == [record.record_digest for record in records]
        and manifest.feedback_cursor == cursor.model_dump(mode="json")
        and manifest.feedback_cursor_digest == feedback_cursor_digest(cursor)
    )
