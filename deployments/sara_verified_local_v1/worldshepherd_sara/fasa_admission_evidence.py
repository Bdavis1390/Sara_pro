from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
)
from .fasa_approval_lease import VerifiedFASAApproval


FASA_ADMISSION_EVIDENCE_SCHEMA = "WS-FASA-ADMISSION-EVIDENCE-V1"


class FASAAdmissionEvidenceError(ValueError):
    pass


class FASAAdmissionEvidence(BaseModel):
    """Tamper-evident record of one FASA admission decision.

    This record is evidence only. It does not authorize or execute an operation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[FASA_ADMISSION_EVIDENCE_SCHEMA] = FASA_ADMISSION_EVIDENCE_SCHEMA
    action_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    capability_level: CapabilityLevel
    policy_id: str = Field(min_length=1, max_length=128)
    evaluation_id: str = Field(min_length=1, max_length=128)
    disposition: FrontierDisposition
    reasons: tuple[str, ...]
    authorization_id: str | None = Field(default=None, min_length=1, max_length=128)
    approval_key_id: str | None = Field(default=None, min_length=1, max_length=128)
    approval_key_fingerprint_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    safety_case_id: str | None = Field(default=None, min_length=1, max_length=128)
    independent_review_id: str | None = Field(default=None, min_length=1, max_length=128)
    provenance_enabled: bool
    overwatch_enabled: bool
    assessed_at: datetime
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise FASAAdmissionEvidenceError("assessed_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_payload(
    *,
    action_id: str,
    model_id: str,
    model_version: str,
    capability_level: CapabilityLevel,
    policy_id: str,
    evaluation_id: str,
    disposition: FrontierDisposition,
    reasons: tuple[str, ...],
    authorization_id: str | None,
    approval_key_id: str | None,
    approval_key_fingerprint_sha256: str | None,
    safety_case_id: str | None,
    independent_review_id: str | None,
    provenance_enabled: bool,
    overwatch_enabled: bool,
    assessed_at: datetime,
) -> bytes:
    payload = {
        "schema": FASA_ADMISSION_EVIDENCE_SCHEMA,
        "action_id": action_id,
        "model_id": model_id,
        "model_version": model_version,
        "capability_level": int(capability_level),
        "policy_id": policy_id,
        "evaluation_id": evaluation_id,
        "disposition": disposition.value,
        "reasons": list(reasons),
        "authorization_id": authorization_id,
        "approval_key_id": approval_key_id,
        "approval_key_fingerprint_sha256": approval_key_fingerprint_sha256,
        "safety_case_id": safety_case_id,
        "independent_review_id": independent_review_id,
        "provenance_enabled": provenance_enabled,
        "overwatch_enabled": overwatch_enabled,
        "assessed_at": _utc_iso(assessed_at),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_admission_evidence(
    candidate: FrontierActionCandidate,
    registry: CapabilityRegistryEntry,
    policy: FrontierSafetyPolicy,
    disposition: FrontierDisposition,
    reasons: list[str] | tuple[str, ...],
    *,
    verified_approval: VerifiedFASAApproval | None = None,
    assessed_at: datetime | None = None,
) -> FASAAdmissionEvidence:
    """Build a deterministic, tamper-evident record from already-evaluated inputs."""

    if candidate.model_id != registry.model_id or candidate.model_version != registry.model_version:
        raise FASAAdmissionEvidenceError(
            "candidate identity/version does not match capability registry"
        )
    if policy.policy_id == "":
        raise FASAAdmissionEvidenceError("policy_id cannot be empty")

    current = (assessed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    normalized_reasons = tuple(str(reason) for reason in reasons)
    if not normalized_reasons:
        raise FASAAdmissionEvidenceError("at least one decision reason is required")

    authorization_id = verified_approval.authorization_id if verified_approval else None
    approval_key_id = verified_approval.key_id if verified_approval else None
    fingerprint = (
        verified_approval.key_fingerprint_sha256 if verified_approval else None
    )
    safety_case_id = verified_approval.safety_case_id if verified_approval else None
    independent_review_id = (
        verified_approval.independent_review_id if verified_approval else None
    )

    if disposition == FrontierDisposition.ALLOW and candidate.capability_level >= policy.human_review_level:
        if verified_approval is None:
            raise FASAAdmissionEvidenceError(
                "ALLOW at or above the human-review level requires verified approval evidence"
            )
        if (
            verified_approval.model_id != candidate.model_id
            or verified_approval.model_version != candidate.model_version
            or verified_approval.action_id != candidate.action_id
            or verified_approval.capability_level != candidate.capability_level
            or verified_approval.policy_id != policy.policy_id
            or verified_approval.evaluation_id != registry.evaluation_id
        ):
            raise FASAAdmissionEvidenceError(
                "verified approval is not bound to the admitted candidate, policy, and evaluation"
            )

    canonical = _canonical_payload(
        action_id=candidate.action_id,
        model_id=candidate.model_id,
        model_version=candidate.model_version,
        capability_level=candidate.capability_level,
        policy_id=policy.policy_id,
        evaluation_id=registry.evaluation_id,
        disposition=disposition,
        reasons=normalized_reasons,
        authorization_id=authorization_id,
        approval_key_id=approval_key_id,
        approval_key_fingerprint_sha256=fingerprint,
        safety_case_id=safety_case_id,
        independent_review_id=independent_review_id,
        provenance_enabled=candidate.provenance_enabled,
        overwatch_enabled=candidate.overwatch_enabled,
        assessed_at=current,
    )
    digest = hashlib.sha256(canonical).hexdigest()

    return FASAAdmissionEvidence(
        action_id=candidate.action_id,
        model_id=candidate.model_id,
        model_version=candidate.model_version,
        capability_level=candidate.capability_level,
        policy_id=policy.policy_id,
        evaluation_id=registry.evaluation_id,
        disposition=disposition,
        reasons=normalized_reasons,
        authorization_id=authorization_id,
        approval_key_id=approval_key_id,
        approval_key_fingerprint_sha256=fingerprint,
        safety_case_id=safety_case_id,
        independent_review_id=independent_review_id,
        provenance_enabled=candidate.provenance_enabled,
        overwatch_enabled=candidate.overwatch_enabled,
        assessed_at=current,
        decision_digest_sha256=digest,
    )


def verify_admission_evidence(evidence: FASAAdmissionEvidence) -> None:
    """Raise if any digest-bound decision field has been changed."""

    expected = hashlib.sha256(
        _canonical_payload(
            action_id=evidence.action_id,
            model_id=evidence.model_id,
            model_version=evidence.model_version,
            capability_level=evidence.capability_level,
            policy_id=evidence.policy_id,
            evaluation_id=evidence.evaluation_id,
            disposition=evidence.disposition,
            reasons=evidence.reasons,
            authorization_id=evidence.authorization_id,
            approval_key_id=evidence.approval_key_id,
            approval_key_fingerprint_sha256=evidence.approval_key_fingerprint_sha256,
            safety_case_id=evidence.safety_case_id,
            independent_review_id=evidence.independent_review_id,
            provenance_enabled=evidence.provenance_enabled,
            overwatch_enabled=evidence.overwatch_enabled,
            assessed_at=evidence.assessed_at,
        )
    ).hexdigest()
    if expected != evidence.decision_digest_sha256:
        raise FASAAdmissionEvidenceError("FASA admission evidence digest mismatch")
