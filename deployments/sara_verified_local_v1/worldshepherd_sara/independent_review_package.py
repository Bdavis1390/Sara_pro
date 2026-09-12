from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .fasa import CapabilityLevel, FrontierDisposition
from .independent_checkpoint_corroboration import (
    IndependentCheckpointCorroboration,
    IndependentCheckpointCorroborationError,
    verify_independent_checkpoint_corroboration,
)
from .independent_evaluator import (
    IndependentEvaluatorError,
    IndependentEvaluatorReport,
    verify_independent_evaluator_report,
)


INDEPENDENT_REVIEW_PACKAGE_SCHEMA = "WS-INDEPENDENT-REVIEW-PACKAGE-V1"
_CLAIMS_BOUNDARY = (
    "Package integrity and internal evidence bindings are verified from supplied "
    "Worldshepherd evidence objects. Signed local ECHO checkpoint membership is "
    "corroborated separately. Monitor identity authentication, immutable/WORM "
    "retention, external anchoring, independent third-party certification, "
    "authorization, FASA readiness, and execution are not established."
)


class IndependentReviewPackageError(ValueError):
    """Raised when reviewer evidence cannot be assembled or verified safely."""


class IndependentReviewPackage(BaseModel):
    """Tamper-evident, non-authorizing evidence package for human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-INDEPENDENT-REVIEW-PACKAGE-V1"] = (
        INDEPENDENT_REVIEW_PACKAGE_SCHEMA
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
    echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_id: str = Field(min_length=1, max_length=200)
    checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_report_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_corroboration_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_binding_status: Literal["CROSS_BOUND"] = "CROSS_BOUND"
    checkpoint_status: Literal["SIGNED_LOCAL_CHECKPOINT_CORROBORATED"] = (
        "SIGNED_LOCAL_CHECKPOINT_CORROBORATED"
    )
    monitor_verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    review_status: Literal["PACKAGE_ASSEMBLED_FOR_HUMAN_REVIEW"] = (
        "PACKAGE_ASSEMBLED_FOR_HUMAN_REVIEW"
    )
    approval_status: Literal["NOT_APPROVED_BY_THIS_PACKAGE"] = (
        "NOT_APPROVED_BY_THIS_PACKAGE"
    )
    authorization_effect: Literal["NONE"] = "NONE"
    readiness_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False
    claims_boundary: str = _CLAIMS_BOUNDARY
    package_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    echo_semantic_sha256: str,
    checkpoint_id: str,
    checkpoint_sha256: str,
    checkpoint_key_fingerprint_sha256: str,
    evaluator_report_digest_sha256: str,
    checkpoint_corroboration_digest_sha256: str,
) -> bytes:
    payload = {
        "schema": INDEPENDENT_REVIEW_PACKAGE_SCHEMA,
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
        "echo_semantic_sha256": echo_semantic_sha256,
        "checkpoint_id": checkpoint_id,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_key_fingerprint_sha256": checkpoint_key_fingerprint_sha256,
        "evaluator_report_digest_sha256": evaluator_report_digest_sha256,
        "checkpoint_corroboration_digest_sha256": checkpoint_corroboration_digest_sha256,
        "evidence_binding_status": "CROSS_BOUND",
        "checkpoint_status": "SIGNED_LOCAL_CHECKPOINT_CORROBORATED",
        "monitor_verification_status": "UNVERIFIED",
        "review_status": "PACKAGE_ASSEMBLED_FOR_HUMAN_REVIEW",
        "approval_status": "NOT_APPROVED_BY_THIS_PACKAGE",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_independent_review_package(
    *,
    evaluator_report: IndependentEvaluatorReport,
    checkpoint_corroboration: IndependentCheckpointCorroboration,
) -> IndependentReviewPackage:
    """Cross-bind verified evidence objects into a human-review package.

    This function is evidence assembly only. It cannot approve an action, mutate
    SARA/ECHO state, create FASA readiness, or apply an execution side effect.
    """

    try:
        verify_independent_evaluator_report(evaluator_report)
    except IndependentEvaluatorError as exc:
        raise IndependentReviewPackageError(
            "independent evaluator report verification failed"
        ) from exc
    try:
        verify_independent_checkpoint_corroboration(checkpoint_corroboration)
    except IndependentCheckpointCorroborationError as exc:
        raise IndependentReviewPackageError(
            "checkpoint corroboration verification failed"
        ) from exc

    if evaluator_report.overwatch_observation_id != checkpoint_corroboration.observation_id:
        raise IndependentReviewPackageError(
            "evaluator/corroboration observation binding mismatch"
        )
    if (
        evaluator_report.overwatch_decision_digest_sha256
        != checkpoint_corroboration.decision_digest_sha256
    ):
        raise IndependentReviewPackageError(
            "evaluator/corroboration decision digest mismatch"
        )
    if (
        evaluator_report.overwatch_echo_semantic_sha256
        != checkpoint_corroboration.echo_semantic_sha256
    ):
        raise IndependentReviewPackageError(
            "evaluator/corroboration ECHO semantic digest mismatch"
        )

    canonical = _canonical_payload(
        review_id=evaluator_report.review_id,
        action_id=evaluator_report.action_id,
        model_id=evaluator_report.model_id,
        model_version=evaluator_report.model_version,
        capability_level=evaluator_report.capability_level,
        fasa_disposition=evaluator_report.fasa_disposition,
        fasa_decision_digest_sha256=evaluator_report.fasa_decision_digest_sha256,
        overwatch_observation_id=evaluator_report.overwatch_observation_id,
        overwatch_monitor_id=evaluator_report.overwatch_monitor_id,
        overwatch_decision_digest_sha256=(
            evaluator_report.overwatch_decision_digest_sha256
        ),
        echo_semantic_sha256=evaluator_report.overwatch_echo_semantic_sha256,
        checkpoint_id=checkpoint_corroboration.checkpoint_id,
        checkpoint_sha256=checkpoint_corroboration.checkpoint_sha256,
        checkpoint_key_fingerprint_sha256=(
            checkpoint_corroboration.checkpoint_key_fingerprint_sha256
        ),
        evaluator_report_digest_sha256=evaluator_report.report_digest_sha256,
        checkpoint_corroboration_digest_sha256=(
            checkpoint_corroboration.corroboration_digest_sha256
        ),
    )

    return IndependentReviewPackage(
        review_id=evaluator_report.review_id,
        action_id=evaluator_report.action_id,
        model_id=evaluator_report.model_id,
        model_version=evaluator_report.model_version,
        capability_level=evaluator_report.capability_level,
        fasa_disposition=evaluator_report.fasa_disposition,
        fasa_decision_digest_sha256=evaluator_report.fasa_decision_digest_sha256,
        overwatch_observation_id=evaluator_report.overwatch_observation_id,
        overwatch_monitor_id=evaluator_report.overwatch_monitor_id,
        overwatch_decision_digest_sha256=(
            evaluator_report.overwatch_decision_digest_sha256
        ),
        echo_semantic_sha256=evaluator_report.overwatch_echo_semantic_sha256,
        checkpoint_id=checkpoint_corroboration.checkpoint_id,
        checkpoint_sha256=checkpoint_corroboration.checkpoint_sha256,
        checkpoint_key_fingerprint_sha256=(
            checkpoint_corroboration.checkpoint_key_fingerprint_sha256
        ),
        evaluator_report_digest_sha256=evaluator_report.report_digest_sha256,
        checkpoint_corroboration_digest_sha256=(
            checkpoint_corroboration.corroboration_digest_sha256
        ),
        package_digest_sha256=hashlib.sha256(canonical).hexdigest(),
    )


def verify_independent_review_package(package: IndependentReviewPackage) -> None:
    """Raise if fixed review boundaries or digest-bound fields changed."""

    invariant_expectations = {
        "schema": INDEPENDENT_REVIEW_PACKAGE_SCHEMA,
        "evidence_binding_status": "CROSS_BOUND",
        "checkpoint_status": "SIGNED_LOCAL_CHECKPOINT_CORROBORATED",
        "monitor_verification_status": "UNVERIFIED",
        "review_status": "PACKAGE_ASSEMBLED_FOR_HUMAN_REVIEW",
        "approval_status": "NOT_APPROVED_BY_THIS_PACKAGE",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    for field_name, expected_value in invariant_expectations.items():
        if getattr(package, field_name) != expected_value:
            raise IndependentReviewPackageError(
                f"independent review package invariant mismatch: {field_name}"
            )

    expected = hashlib.sha256(
        _canonical_payload(
            review_id=package.review_id,
            action_id=package.action_id,
            model_id=package.model_id,
            model_version=package.model_version,
            capability_level=package.capability_level,
            fasa_disposition=package.fasa_disposition,
            fasa_decision_digest_sha256=package.fasa_decision_digest_sha256,
            overwatch_observation_id=package.overwatch_observation_id,
            overwatch_monitor_id=package.overwatch_monitor_id,
            overwatch_decision_digest_sha256=package.overwatch_decision_digest_sha256,
            echo_semantic_sha256=package.echo_semantic_sha256,
            checkpoint_id=package.checkpoint_id,
            checkpoint_sha256=package.checkpoint_sha256,
            checkpoint_key_fingerprint_sha256=(
                package.checkpoint_key_fingerprint_sha256
            ),
            evaluator_report_digest_sha256=package.evaluator_report_digest_sha256,
            checkpoint_corroboration_digest_sha256=(
                package.checkpoint_corroboration_digest_sha256
            ),
        )
    ).hexdigest()
    if expected != package.package_digest_sha256:
        raise IndependentReviewPackageError(
            "independent review package digest mismatch"
        )
