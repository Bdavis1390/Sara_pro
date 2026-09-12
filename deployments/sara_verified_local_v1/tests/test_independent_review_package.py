from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
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
from worldshepherd_sara.independent_checkpoint_corroboration import (
    corroborate_overwatch_checkpoint,
)
from worldshepherd_sara.independent_evaluator import (
    build_independent_evaluator_report,
)
from worldshepherd_sara.independent_review_package import (
    IndependentReviewPackageError,
    build_independent_review_package,
    verify_independent_review_package,
)
from worldshepherd_sara.overwatch_attestation_contract import (
    OverwatchAttestationContract,
)
from worldshepherd_sara.overwatch_provenance import (
    deliver_overwatch_intent_provenance,
)
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 2, 5, tzinfo=timezone.utc)


def _evidence_set(tmp_path, echo_checkpoint_key, *, suffix: str):
    key, _path = echo_checkpoint_key
    action_id = f"ACTION-REVIEW-PACKAGE-{suffix}"
    model_id = "MODEL-REVIEW-PACKAGE-1"
    model_version = "v1"

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
        evaluation_id=f"EVAL-REVIEW-PACKAGE-{suffix}",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id=f"POLICY-REVIEW-PACKAGE-{suffix}")
    disposition, reasons = evaluate_frontier_action(candidate, registry, policy)
    admission = build_admission_evidence(
        candidate,
        registry,
        policy,
        disposition,
        reasons,
        assessed_at=NOW,
    )

    observation = OverwatchObservation(
        observation_id=f"OBS-REVIEW-PACKAGE-{suffix}",
        action_id=action_id,
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW + timedelta(seconds=1),
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    attestation = OverwatchAttestationContract(
        attestation_id=f"ATTEST-REVIEW-PACKAGE-{suffix}",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce=f"nonce-review-package-{suffix}-0001",
    )

    sara = DurableStore(tmp_path / f"sara-{suffix}")
    echo = EchoEventStore((tmp_path / f"echo-{suffix}").resolve())
    decision = classify_overwatch_observation(observation)
    intent = record_overwatch_containment_intent(
        sara,
        decision=decision,
        now=NOW + timedelta(seconds=3),
    )
    receipt = deliver_overwatch_intent_provenance(
        sara,
        echo,
        intent=intent,
    )

    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-INDEPENDENT-REVIEW-PACKAGE-V1",
    )
    bundle = manager.create_checkpoint()
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=bundle,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    evaluator_report = build_independent_evaluator_report(
        review_id=f"INDEPENDENT-REVIEW-PACKAGE-{suffix}",
        admission_evidence=admission,
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )
    return {
        "admission": admission,
        "attestation": attestation,
        "receipt": receipt,
        "corroboration": corroboration,
        "evaluator_report": evaluator_report,
    }


def test_independent_review_package_cross_binds_verified_evidence(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="VALID")
    package = build_independent_review_package(
        evaluator_report=evidence["evaluator_report"],
        checkpoint_corroboration=evidence["corroboration"],
    )

    assert package.evidence_binding_status == "CROSS_BOUND"
    assert package.checkpoint_status == "SIGNED_LOCAL_CHECKPOINT_CORROBORATED"
    assert package.monitor_verification_status == "UNVERIFIED"
    assert package.review_status == "PACKAGE_ASSEMBLED_FOR_HUMAN_REVIEW"
    assert package.approval_status == "NOT_APPROVED_BY_THIS_PACKAGE"
    assert package.authorization_effect == "NONE"
    assert package.readiness_effect == "NONE"
    assert package.execution_effect_applied is False
    verify_independent_review_package(package)


def test_individually_valid_evidence_with_different_observations_is_rejected(
    tmp_path,
    echo_checkpoint_key,
):
    first = _evidence_set(tmp_path, echo_checkpoint_key, suffix="OBS-A")
    second = _evidence_set(tmp_path, echo_checkpoint_key, suffix="OBS-B")

    with pytest.raises(
        IndependentReviewPackageError,
        match="observation binding mismatch",
    ):
        build_independent_review_package(
            evaluator_report=first["evaluator_report"],
            checkpoint_corroboration=second["corroboration"],
        )


def test_evaluator_receipt_decision_digest_must_match_corroborated_digest(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="DECISION")
    forged_receipt = evidence["receipt"].model_copy(
        update={"decision_digest_sha256": "f" * 64}
    )
    forged_report = build_independent_evaluator_report(
        review_id="INDEPENDENT-REVIEW-PACKAGE-FORGED-DECISION",
        admission_evidence=evidence["admission"],
        overwatch_attestation=evidence["attestation"],
        overwatch_provenance=forged_receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )

    with pytest.raises(
        IndependentReviewPackageError,
        match="decision digest mismatch",
    ):
        build_independent_review_package(
            evaluator_report=forged_report,
            checkpoint_corroboration=evidence["corroboration"],
        )


def test_evaluator_receipt_echo_digest_must_match_corroborated_digest(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="ECHO")
    forged_receipt = evidence["receipt"].model_copy(
        update={"echo_semantic_sha256": "f" * 64}
    )
    forged_report = build_independent_evaluator_report(
        review_id="INDEPENDENT-REVIEW-PACKAGE-FORGED-ECHO",
        admission_evidence=evidence["admission"],
        overwatch_attestation=evidence["attestation"],
        overwatch_provenance=forged_receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )

    with pytest.raises(
        IndependentReviewPackageError,
        match="ECHO semantic digest mismatch",
    ):
        build_independent_review_package(
            evaluator_report=forged_report,
            checkpoint_corroboration=evidence["corroboration"],
        )


def test_tampered_evaluator_report_is_rejected_before_packaging(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="REPORT-TAMPER")
    tampered = evidence["evaluator_report"].model_copy(
        update={"action_id": "ACTION-TAMPERED"}
    )

    with pytest.raises(
        IndependentReviewPackageError,
        match="evaluator report verification failed",
    ):
        build_independent_review_package(
            evaluator_report=tampered,
            checkpoint_corroboration=evidence["corroboration"],
        )


def test_tampered_checkpoint_corroboration_is_rejected_before_packaging(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="CORR-TAMPER")
    tampered = evidence["corroboration"].model_copy(
        update={"checkpoint_id": "CHECKPOINT-TAMPERED"}
    )

    with pytest.raises(
        IndependentReviewPackageError,
        match="checkpoint corroboration verification failed",
    ):
        build_independent_review_package(
            evaluator_report=evidence["evaluator_report"],
            checkpoint_corroboration=tampered,
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("evidence_binding_status", "UNBOUND"),
        ("checkpoint_status", "UNCHECKED"),
        ("monitor_verification_status", "VERIFIED"),
        ("review_status", "APPROVED"),
        ("approval_status", "APPROVED"),
        ("authorization_effect", "ALLOW"),
        ("readiness_effect", "READY"),
        ("execution_effect_applied", True),
        ("claims_boundary", "all guarantees established"),
    ],
)
def test_review_package_verifier_rejects_boundary_tampering(
    tmp_path,
    echo_checkpoint_key,
    field_name,
    unsafe_value,
):
    evidence = _evidence_set(
        tmp_path,
        echo_checkpoint_key,
        suffix=f"INVARIANT-{field_name}",
    )
    package = build_independent_review_package(
        evaluator_report=evidence["evaluator_report"],
        checkpoint_corroboration=evidence["corroboration"],
    )
    tampered = package.model_copy(update={field_name: unsafe_value})

    with pytest.raises(IndependentReviewPackageError, match="invariant mismatch"):
        verify_independent_review_package(tampered)


def test_review_package_digest_detects_bound_field_tampering(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="DIGEST")
    package = build_independent_review_package(
        evaluator_report=evidence["evaluator_report"],
        checkpoint_corroboration=evidence["corroboration"],
    )
    tampered = package.model_copy(update={"action_id": "ACTION-FORGED"})

    with pytest.raises(IndependentReviewPackageError, match="package digest mismatch"):
        verify_independent_review_package(tampered)


def test_review_package_cannot_validate_as_fasa_readiness_or_consumption(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="NONAUTHORITY")
    package = build_independent_review_package(
        evaluator_report=evidence["evaluator_report"],
        checkpoint_corroboration=evidence["corroboration"],
    )
    payload = package.model_dump(mode="json")

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(payload)
    with pytest.raises(ValidationError):
        FASAExecutionReadinessConsumption.model_validate(payload)
