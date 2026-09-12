from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .fasa import CapabilityLevel, FrontierDisposition
from .fasa_admission_evidence import (
    FASAAdmissionEvidence,
    FASAAdmissionEvidenceError,
    verify_admission_evidence,
)
from .overwatch_attestation_contract import OverwatchAttestationContract
from .overwatch_provenance import OverwatchProvenanceReceipt


INDEPENDENT_EVALUATOR_REPORT_SCHEMA = "WS-INDEPENDENT-EVALUATOR-REPORT-V1"


class IndependentEvaluatorError(ValueError):
    """Raised when review evidence cannot be bound or verified safely."""


class IndependentEvaluatorReport(BaseModel):
    """Tamper-evident read-only evidence package for an independent reviewer.

    This report is intentionally non-authorizing. It cannot create PRIME approval,
    FASA execution readiness, OVERWATCH authority, or an execution side effect.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-INDEPENDENT-EVALUATOR-REPORT-V1"] = (
        INDEPENDENT_EVALUATOR_REPORT_SCHEMA
    )
    review_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=160)
    model_version: str = Field(min_length=1, max_length=160)
    capability_level: CapabilityLevel
    fasa_disposition: FrontierDisposition
    fasa_decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    overwatch_observation_id: str = Field(min_length=1, max_length=160)
    overwatch_monitor_id: str = Field(min_length=1, max_length=160)
    overwatch_decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    overwatch_echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    monitor_verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    evidence_binding_status: Literal["BOUND"] = "BOUND"
    review_outcome: Literal["EVIDENCE_ONLY"] = "EVIDENCE_ONLY"
    authority_status: Literal["NO_AUTHORITY"] = "NO_AUTHORITY"
    readiness_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False
    findings: tuple[str, ...] = Field(min_length=1, max_length=32)
    evaluated_at: datetime
    report_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise IndependentEvaluatorError("evaluated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_payload(
    *,
    review_id: str,
    action_id: str,
    model_id: str,
    model_version: str,
    capability_level: CapabilityLevel,
    fasa_disposition: FrontierDisposition,
    fasa_decision_digest_sha256: str,
    overwatch_observation_id: str,
    overwatch_monitor_id: str,
    overwatch_decision_digest_sha256: str,
    overwatch_echo_semantic_sha256: str,
    findings: tuple[str, ...],
    evaluated_at: datetime,
) -> bytes:
    payload = {
        "schema": INDEPENDENT_EVALUATOR_REPORT_SCHEMA,
        "review_id": review_id,
        "action_id": action_id,
        "model_id": model_id,
        "model_version": model_version,
        "capability_level": int(capability_level),
        "fasa_disposition": fasa_disposition.value,
        "fasa_decision_digest_sha256": fasa_decision_digest_sha256,
        "overwatch_observation_id": overwatch_observation_id,
        "overwatch_monitor_id": overwatch_monitor_id,
        "overwatch_decision_digest_sha256": overwatch_decision_digest_sha256,
        "overwatch_echo_semantic_sha256": overwatch_echo_semantic_sha256,
        "monitor_verification_status": "UNVERIFIED",
        "evidence_binding_status": "BOUND",
        "review_outcome": "EVIDENCE_ONLY",
        "authority_status": "NO_AUTHORITY",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "findings": list(findings),
        "evaluated_at": _utc_iso(evaluated_at),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_independent_evaluator_report(
    *,
    review_id: str,
    admission_evidence: FASAAdmissionEvidence,
    overwatch_attestation: OverwatchAttestationContract,
    overwatch_provenance: OverwatchProvenanceReceipt,
    evaluated_at: datetime | None = None,
) -> IndependentEvaluatorReport:
    """Bind existing safety evidence into a non-authorizing reviewer report.

    The function validates cross-object identity and digest relationships but
    deliberately has no access to SARA registry mutation, PRIME signing, FASA
    readiness creation, or execution-consumption functions.
    """

    if not review_id:
        raise IndependentEvaluatorError("review_id cannot be empty")

    try:
        verify_admission_evidence(admission_evidence)
    except FASAAdmissionEvidenceError as exc:
        raise IndependentEvaluatorError(
            "FASA admission evidence failed integrity verification"
        ) from exc

    observation = overwatch_attestation.observation
    if overwatch_attestation.verification_status != "UNVERIFIED":
        raise IndependentEvaluatorError(
            "current OVERWATCH attestation contract must remain UNVERIFIED"
        )
    if overwatch_attestation.authorization_effect != "NONE":
        raise IndependentEvaluatorError("OVERWATCH attestation cannot confer authority")
    if overwatch_attestation.execution_effect_applied is not False:
        raise IndependentEvaluatorError(
            "OVERWATCH attestation cannot claim an execution side effect"
        )
    if overwatch_provenance.authorization_effect != "NONE":
        raise IndependentEvaluatorError("OVERWATCH provenance cannot confer authority")
    if overwatch_provenance.execution_effect_applied is not False:
        raise IndependentEvaluatorError(
            "OVERWATCH provenance cannot claim an execution side effect"
        )

    if overwatch_provenance.observation_id != observation.observation_id:
        raise IndependentEvaluatorError(
            "OVERWATCH provenance observation binding mismatch"
        )
    if admission_evidence.action_id != observation.action_id:
        raise IndependentEvaluatorError("FASA/OVERWATCH action binding mismatch")
    if admission_evidence.model_id != observation.model_id:
        raise IndependentEvaluatorError("FASA/OVERWATCH model binding mismatch")
    if admission_evidence.model_version != observation.model_version:
        raise IndependentEvaluatorError("FASA/OVERWATCH model-version binding mismatch")

    current = evaluated_at or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise IndependentEvaluatorError("evaluated_at must be timezone-aware")
    current = current.astimezone(timezone.utc)

    findings = (
        "FASA admission evidence digest verified.",
        "FASA and OVERWATCH action/model/version bindings agree.",
        "OVERWATCH provenance is evidence only and confers no authorization effect.",
        "OVERWATCH monitor identity remains UNVERIFIED under the current attestation contract.",
        "This evaluator report cannot create execution readiness or execution authority.",
    )

    canonical = _canonical_payload(
        review_id=review_id,
        action_id=admission_evidence.action_id,
        model_id=admission_evidence.model_id,
        model_version=admission_evidence.model_version,
        capability_level=admission_evidence.capability_level,
        fasa_disposition=admission_evidence.disposition,
        fasa_decision_digest_sha256=admission_evidence.decision_digest_sha256,
        overwatch_observation_id=observation.observation_id,
        overwatch_monitor_id=observation.monitor_id,
        overwatch_decision_digest_sha256=overwatch_provenance.decision_digest_sha256,
        overwatch_echo_semantic_sha256=overwatch_provenance.echo_semantic_sha256,
        findings=findings,
        evaluated_at=current,
    )
    digest = hashlib.sha256(canonical).hexdigest()

    return IndependentEvaluatorReport(
        review_id=review_id,
        action_id=admission_evidence.action_id,
        model_id=admission_evidence.model_id,
        model_version=admission_evidence.model_version,
        capability_level=admission_evidence.capability_level,
        fasa_disposition=admission_evidence.disposition,
        fasa_decision_digest_sha256=admission_evidence.decision_digest_sha256,
        overwatch_observation_id=observation.observation_id,
        overwatch_monitor_id=observation.monitor_id,
        overwatch_decision_digest_sha256=overwatch_provenance.decision_digest_sha256,
        overwatch_echo_semantic_sha256=overwatch_provenance.echo_semantic_sha256,
        findings=findings,
        evaluated_at=current,
        report_digest_sha256=digest,
    )


def verify_independent_evaluator_report(report: IndependentEvaluatorReport) -> None:
    """Raise if any digest-bound reviewer field has changed."""

    expected = hashlib.sha256(
        _canonical_payload(
            review_id=report.review_id,
            action_id=report.action_id,
            model_id=report.model_id,
            model_version=report.model_version,
            capability_level=report.capability_level,
            fasa_disposition=report.fasa_disposition,
            fasa_decision_digest_sha256=report.fasa_decision_digest_sha256,
            overwatch_observation_id=report.overwatch_observation_id,
            overwatch_monitor_id=report.overwatch_monitor_id,
            overwatch_decision_digest_sha256=report.overwatch_decision_digest_sha256,
            overwatch_echo_semantic_sha256=report.overwatch_echo_semantic_sha256,
            findings=report.findings,
            evaluated_at=report.evaluated_at,
        )
    ).hexdigest()
    if expected != report.report_digest_sha256:
        raise IndependentEvaluatorError("independent evaluator report digest mismatch")
