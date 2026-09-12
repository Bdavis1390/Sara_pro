from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .fasa_admission_evidence import FASAAdmissionEvidence
from .independent_checkpoint_corroboration import (
    IndependentCheckpointCorroboration,
    IndependentCheckpointCorroborationError,
    corroborate_overwatch_checkpoint,
    verify_independent_checkpoint_corroboration,
)
from .independent_evaluator import (
    IndependentEvaluatorError,
    IndependentEvaluatorReport,
    build_independent_evaluator_report,
    verify_independent_evaluator_report,
)
from .independent_review_package import (
    IndependentReviewPackage,
    IndependentReviewPackageError,
    build_independent_review_package,
    verify_independent_review_package,
)
from .overwatch_attestation_contract import OverwatchAttestationContract
from .overwatch_provenance import OverwatchProvenanceReceipt


INDEPENDENT_REVIEW_EXPORT_SCHEMA = "WS-INDEPENDENT-REVIEW-EXPORT-BUNDLE-V1"
_CLAIMS_BOUNDARY = (
    "Self-contained inputs are supplied for reproduction of Worldshepherd's local "
    "admission-integrity, evaluator-binding, deterministic OVERWATCH decision, "
    "signed local ECHO checkpoint, and review-package checks. This does not "
    "authenticate the monitor, establish immutable/WORM retention or external "
    "anchoring, constitute independent third-party certification, authorize an "
    "action, create FASA readiness, or execute a side effect."
)


class IndependentReviewExportError(ValueError):
    """Raised when a portable reviewer bundle cannot be reproduced safely."""


class IndependentReviewExportBundle(BaseModel):
    """Portable, tamper-evident evidence inputs for independent human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-INDEPENDENT-REVIEW-EXPORT-BUNDLE-V1"] = (
        INDEPENDENT_REVIEW_EXPORT_SCHEMA
    )
    review_package: IndependentReviewPackage
    evaluator_report: IndependentEvaluatorReport
    checkpoint_corroboration: IndependentCheckpointCorroboration
    admission_evidence: FASAAdmissionEvidence
    overwatch_attestation: OverwatchAttestationContract
    overwatch_provenance: OverwatchProvenanceReceipt
    checkpoint_bundle: dict[str, Any]
    expected_checkpoint_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reproduction_status: Literal["SELF_CONTAINED_EVIDENCE_INPUTS"] = (
        "SELF_CONTAINED_EVIDENCE_INPUTS"
    )
    monitor_verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    review_status: Literal["HUMAN_REVIEW_REQUIRED"] = "HUMAN_REVIEW_REQUIRED"
    approval_status: Literal["NOT_APPROVED_BY_THIS_BUNDLE"] = (
        "NOT_APPROVED_BY_THIS_BUNDLE"
    )
    authorization_effect: Literal["NONE"] = "NONE"
    readiness_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False
    claims_boundary: str = _CLAIMS_BOUNDARY
    bundle_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _canonical_payload(
    *,
    review_package: IndependentReviewPackage,
    evaluator_report: IndependentEvaluatorReport,
    checkpoint_corroboration: IndependentCheckpointCorroboration,
    admission_evidence: FASAAdmissionEvidence,
    overwatch_attestation: OverwatchAttestationContract,
    overwatch_provenance: OverwatchProvenanceReceipt,
    checkpoint_bundle: dict[str, Any],
    expected_checkpoint_key_fingerprint_sha256: str,
) -> bytes:
    payload = {
        "schema": INDEPENDENT_REVIEW_EXPORT_SCHEMA,
        "review_package": review_package.model_dump(mode="json"),
        "evaluator_report": evaluator_report.model_dump(mode="json"),
        "checkpoint_corroboration": checkpoint_corroboration.model_dump(mode="json"),
        "admission_evidence": admission_evidence.model_dump(mode="json"),
        "overwatch_attestation": overwatch_attestation.model_dump(mode="json"),
        "overwatch_provenance": overwatch_provenance.model_dump(mode="json"),
        "checkpoint_bundle": checkpoint_bundle,
        "expected_checkpoint_key_fingerprint_sha256": (
            expected_checkpoint_key_fingerprint_sha256
        ),
        "reproduction_status": "SELF_CONTAINED_EVIDENCE_INPUTS",
        "monitor_verification_status": "UNVERIFIED",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "approval_status": "NOT_APPROVED_BY_THIS_BUNDLE",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IndependentReviewExportError(
            "review export contains non-JSON evidence input"
        ) from exc


def _reproduce(bundle: IndependentReviewExportBundle) -> None:
    try:
        verify_independent_evaluator_report(bundle.evaluator_report)
    except IndependentEvaluatorError as exc:
        raise IndependentReviewExportError(
            "independent evaluator report verification failed"
        ) from exc
    try:
        verify_independent_checkpoint_corroboration(bundle.checkpoint_corroboration)
    except IndependentCheckpointCorroborationError as exc:
        raise IndependentReviewExportError(
            "checkpoint corroboration verification failed"
        ) from exc
    try:
        verify_independent_review_package(bundle.review_package)
    except IndependentReviewPackageError as exc:
        raise IndependentReviewExportError(
            "independent review package verification failed"
        ) from exc

    try:
        reproduced_report = build_independent_evaluator_report(
            review_id=bundle.evaluator_report.review_id,
            admission_evidence=bundle.admission_evidence,
            overwatch_attestation=bundle.overwatch_attestation,
            overwatch_provenance=bundle.overwatch_provenance,
            evaluated_at=bundle.evaluator_report.evaluated_at,
        )
    except IndependentEvaluatorError as exc:
        raise IndependentReviewExportError(
            "independent evaluator reproduction failed"
        ) from exc
    if reproduced_report.model_dump(mode="json") != bundle.evaluator_report.model_dump(
        mode="json"
    ):
        raise IndependentReviewExportError(
            "reproduced evaluator report does not match supplied report"
        )

    try:
        reproduced_corroboration = corroborate_overwatch_checkpoint(
            overwatch_attestation=bundle.overwatch_attestation,
            overwatch_provenance=bundle.overwatch_provenance,
            checkpoint_bundle=bundle.checkpoint_bundle,
            expected_checkpoint_key_fingerprint_sha256=(
                bundle.expected_checkpoint_key_fingerprint_sha256
            ),
        )
    except IndependentCheckpointCorroborationError as exc:
        raise IndependentReviewExportError(
            "signed checkpoint corroboration reproduction failed"
        ) from exc
    if reproduced_corroboration.model_dump(mode="json") != (
        bundle.checkpoint_corroboration.model_dump(mode="json")
    ):
        raise IndependentReviewExportError(
            "reproduced checkpoint corroboration does not match supplied proof"
        )

    try:
        reproduced_package = build_independent_review_package(
            evaluator_report=reproduced_report,
            checkpoint_corroboration=reproduced_corroboration,
        )
    except IndependentReviewPackageError as exc:
        raise IndependentReviewExportError(
            "independent review package reproduction failed"
        ) from exc
    if reproduced_package.model_dump(mode="json") != bundle.review_package.model_dump(
        mode="json"
    ):
        raise IndependentReviewExportError(
            "reproduced review package does not match supplied package"
        )


def build_independent_review_export_bundle(
    *,
    review_package: IndependentReviewPackage,
    evaluator_report: IndependentEvaluatorReport,
    checkpoint_corroboration: IndependentCheckpointCorroboration,
    admission_evidence: FASAAdmissionEvidence,
    overwatch_attestation: OverwatchAttestationContract,
    overwatch_provenance: OverwatchProvenanceReceipt,
    checkpoint_bundle: dict[str, Any],
    expected_checkpoint_key_fingerprint_sha256: str,
) -> IndependentReviewExportBundle:
    """Assemble a self-contained reviewer bundle with no runtime authority."""

    provisional = IndependentReviewExportBundle(
        review_package=review_package,
        evaluator_report=evaluator_report,
        checkpoint_corroboration=checkpoint_corroboration,
        admission_evidence=admission_evidence,
        overwatch_attestation=overwatch_attestation,
        overwatch_provenance=overwatch_provenance,
        checkpoint_bundle=checkpoint_bundle,
        expected_checkpoint_key_fingerprint_sha256=(
            expected_checkpoint_key_fingerprint_sha256
        ),
        bundle_digest_sha256="0" * 64,
    )
    _reproduce(provisional)
    canonical = _canonical_payload(
        review_package=review_package,
        evaluator_report=evaluator_report,
        checkpoint_corroboration=checkpoint_corroboration,
        admission_evidence=admission_evidence,
        overwatch_attestation=overwatch_attestation,
        overwatch_provenance=overwatch_provenance,
        checkpoint_bundle=checkpoint_bundle,
        expected_checkpoint_key_fingerprint_sha256=(
            expected_checkpoint_key_fingerprint_sha256
        ),
    )
    return provisional.model_copy(
        update={"bundle_digest_sha256": hashlib.sha256(canonical).hexdigest()}
    )


def verify_independent_review_export_bundle(
    bundle: IndependentReviewExportBundle,
) -> None:
    """Reproduce all supplied evidence checks and verify the export digest."""

    invariant_expectations = {
        "schema": INDEPENDENT_REVIEW_EXPORT_SCHEMA,
        "reproduction_status": "SELF_CONTAINED_EVIDENCE_INPUTS",
        "monitor_verification_status": "UNVERIFIED",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "approval_status": "NOT_APPROVED_BY_THIS_BUNDLE",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    for field_name, expected_value in invariant_expectations.items():
        if getattr(bundle, field_name) != expected_value:
            raise IndependentReviewExportError(
                f"independent review export invariant mismatch: {field_name}"
            )

    _reproduce(bundle)
    expected = hashlib.sha256(
        _canonical_payload(
            review_package=bundle.review_package,
            evaluator_report=bundle.evaluator_report,
            checkpoint_corroboration=bundle.checkpoint_corroboration,
            admission_evidence=bundle.admission_evidence,
            overwatch_attestation=bundle.overwatch_attestation,
            overwatch_provenance=bundle.overwatch_provenance,
            checkpoint_bundle=bundle.checkpoint_bundle,
            expected_checkpoint_key_fingerprint_sha256=(
                bundle.expected_checkpoint_key_fingerprint_sha256
            ),
        )
    ).hexdigest()
    if expected != bundle.bundle_digest_sha256:
        raise IndependentReviewExportError(
            "independent review export bundle digest mismatch"
        )
