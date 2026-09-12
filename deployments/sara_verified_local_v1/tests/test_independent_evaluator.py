from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierSafetyPolicy,
    evaluate_frontier_action,
)
from worldshepherd_sara.fasa_admission_evidence import build_admission_evidence
from worldshepherd_sara.fasa_runtime_gate import (
    FASAEchoExecutionReadiness,
    FASAExecutionReadinessConsumption,
)
from worldshepherd_sara.independent_evaluator import (
    IndependentEvaluatorError,
    build_independent_evaluator_report,
    verify_independent_evaluator_report,
)
from worldshepherd_sara.overwatch_attestation_contract import (
    OverwatchAttestationContract,
)
from worldshepherd_sara.overwatch_provenance import OverwatchProvenanceReceipt
from worldshepherd_sara.overwatch_tripwire import OverwatchObservation


NOW = datetime(2026, 9, 12, 1, 15, tzinfo=timezone.utc)


def _admission_evidence(
    *,
    action_id: str = "ACTION-REVIEW-1",
    model_id: str = "MODEL-REVIEW-1",
    model_version: str = "v1",
):
    candidate = FrontierActionCandidate(
        action_id=action_id,
        model_id=model_id,
        model_version=model_version,
        capability_level=CapabilityLevel.F1,
        reversible=True,
        consequential_external_effect=False,
    )
    registry = CapabilityRegistryEntry(
        model_id=model_id,
        model_version=model_version,
        assessed_level=CapabilityLevel.F1,
        maximum_authorized_level=CapabilityLevel.F1,
        evaluation_id="EVAL-REVIEW-1",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id="POLICY-REVIEW-1")
    disposition, reasons = evaluate_frontier_action(candidate, registry, policy)
    return build_admission_evidence(
        candidate,
        registry,
        policy,
        disposition,
        reasons,
        assessed_at=NOW,
    )


def _attestation(
    *,
    observation_id: str = "OBS-REVIEW-1",
    action_id: str = "ACTION-REVIEW-1",
    model_id: str = "MODEL-REVIEW-1",
    model_version: str = "v1",
):
    observation = OverwatchObservation(
        observation_id=observation_id,
        action_id=action_id,
        monitor_id="OVERWATCH-REVIEW-1",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW,
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(),
    )
    return OverwatchAttestationContract(
        attestation_id="ATTEST-REVIEW-1",
        observation=observation,
        issued_at=NOW + timedelta(seconds=1),
        expires_at=NOW + timedelta(seconds=11),
        nonce="nonce-independent-0001",
    )


def _receipt(*, observation_id: str = "OBS-REVIEW-1"):
    return OverwatchProvenanceReceipt(
        observation_id=observation_id,
        provenance_event_id="SARA-EVENT-OVERWATCH-REVIEW-1",
        decision_digest_sha256="a" * 64,
        echo_semantic_sha256="b" * 64,
        echo_delivery_count=1,
    )


def _report():
    return build_independent_evaluator_report(
        review_id="INDEPENDENT-REVIEW-1",
        admission_evidence=_admission_evidence(),
        overwatch_attestation=_attestation(),
        overwatch_provenance=_receipt(),
        evaluated_at=NOW + timedelta(seconds=20),
    )


def test_independent_evaluator_report_is_non_authorizing_and_verifiable():
    report = _report()

    assert report.monitor_verification_status == "UNVERIFIED"
    assert report.evidence_binding_status == "BOUND"
    assert report.review_outcome == "EVIDENCE_ONLY"
    assert report.authority_status == "NO_AUTHORITY"
    assert report.readiness_effect == "NONE"
    assert report.execution_effect_applied is False
    verify_independent_evaluator_report(report)


def test_tampered_fasa_admission_evidence_is_rejected():
    admission = _admission_evidence()
    tampered = admission.model_copy(update={"action_id": "ACTION-TAMPERED"})

    with pytest.raises(
        IndependentEvaluatorError,
        match="FASA admission evidence failed integrity verification",
    ):
        build_independent_evaluator_report(
            review_id="INDEPENDENT-REVIEW-TAMPER",
            admission_evidence=tampered,
            overwatch_attestation=_attestation(),
            overwatch_provenance=_receipt(),
            evaluated_at=NOW + timedelta(seconds=20),
        )


def test_overwatch_provenance_observation_binding_mismatch_is_rejected():
    with pytest.raises(
        IndependentEvaluatorError,
        match="OVERWATCH provenance observation binding mismatch",
    ):
        build_independent_evaluator_report(
            review_id="INDEPENDENT-REVIEW-OBS-MISMATCH",
            admission_evidence=_admission_evidence(),
            overwatch_attestation=_attestation(),
            overwatch_provenance=_receipt(observation_id="OBS-OTHER"),
            evaluated_at=NOW + timedelta(seconds=20),
        )


@pytest.mark.parametrize(
    ("attestation", "message"),
    [
        (
            _attestation(action_id="ACTION-OTHER"),
            "FASA/OVERWATCH action binding mismatch",
        ),
        (
            _attestation(model_id="MODEL-OTHER"),
            "FASA/OVERWATCH model binding mismatch",
        ),
        (
            _attestation(model_version="v2"),
            "FASA/OVERWATCH model-version binding mismatch",
        ),
    ],
)
def test_fasa_overwatch_identity_mismatches_fail_closed(attestation, message):
    with pytest.raises(IndependentEvaluatorError, match=message):
        build_independent_evaluator_report(
            review_id="INDEPENDENT-REVIEW-BINDING-MISMATCH",
            admission_evidence=_admission_evidence(),
            overwatch_attestation=attestation,
            overwatch_provenance=_receipt(),
            evaluated_at=NOW + timedelta(seconds=20),
        )


def test_evaluator_rejects_naive_evaluation_timestamp():
    with pytest.raises(IndependentEvaluatorError, match="timezone-aware"):
        build_independent_evaluator_report(
            review_id="INDEPENDENT-REVIEW-NAIVE-TIME",
            admission_evidence=_admission_evidence(),
            overwatch_attestation=_attestation(),
            overwatch_provenance=_receipt(),
            evaluated_at=datetime(2026, 9, 12, 1, 15),
        )


def test_report_digest_detects_bound_field_tampering():
    report = _report()
    tampered = report.model_copy(update={"action_id": "ACTION-TAMPERED"})

    with pytest.raises(IndependentEvaluatorError, match="report digest mismatch"):
        verify_independent_evaluator_report(tampered)


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("monitor_verification_status", "VERIFIED"),
        ("evidence_binding_status", "UNBOUND"),
        ("review_outcome", "APPROVED"),
        ("authority_status", "AUTHORIZED"),
        ("readiness_effect", "READY"),
        ("execution_effect_applied", True),
    ],
)
def test_report_verifier_rejects_non_authority_invariant_tampering(
    field_name,
    unsafe_value,
):
    report = _report()
    tampered = report.model_copy(update={field_name: unsafe_value})

    with pytest.raises(IndependentEvaluatorError, match="invariant mismatch"):
        verify_independent_evaluator_report(tampered)


def test_evaluator_report_cannot_validate_as_fasa_readiness_or_consumption():
    payload = _report().model_dump(mode="json")

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(payload)
    with pytest.raises(ValidationError):
        FASAExecutionReadinessConsumption.model_validate(payload)
