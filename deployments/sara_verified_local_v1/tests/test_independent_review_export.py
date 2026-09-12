from __future__ import annotations

import copy
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
from worldshepherd_sara.independent_evaluator import build_independent_evaluator_report
from worldshepherd_sara.independent_review_export import (
    IndependentReviewExportError,
    build_independent_review_export_bundle,
    verify_independent_review_export_bundle,
)
from worldshepherd_sara.independent_review_package import build_independent_review_package
from worldshepherd_sara.overwatch_attestation_contract import OverwatchAttestationContract
from worldshepherd_sara.overwatch_provenance import deliver_overwatch_intent_provenance
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)


def _evidence_set(tmp_path, echo_checkpoint_key, *, suffix: str):
    key, _path = echo_checkpoint_key
    action_id = f"ACTION-EXPORT-{suffix}"
    model_id = f"MODEL-EXPORT-{suffix}"
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
        evaluation_id=f"EVAL-EXPORT-{suffix}",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id=f"POLICY-EXPORT-{suffix}")
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
        observation_id=f"OBS-EXPORT-{suffix}",
        action_id=action_id,
        monitor_id="OVERWATCH-EXPORT-REVIEWER",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW + timedelta(seconds=1),
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    attestation = OverwatchAttestationContract(
        attestation_id=f"ATTEST-EXPORT-{suffix}",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce=f"nonce-export-{suffix}-0001",
    )

    sara = DurableStore(tmp_path / f"sara-export-{suffix}")
    echo = EchoEventStore((tmp_path / f"echo-export-{suffix}").resolve())
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
        key_id=f"ECHO-CHECKPOINT-EXPORT-{suffix}",
    )
    checkpoint = manager.create_checkpoint()
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    report = build_independent_evaluator_report(
        review_id=f"INDEPENDENT-EXPORT-REVIEW-{suffix}",
        admission_evidence=admission,
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )
    package = build_independent_review_package(
        evaluator_report=report,
        checkpoint_corroboration=corroboration,
    )
    export = build_independent_review_export_bundle(
        review_package=package,
        evaluator_report=report,
        checkpoint_corroboration=corroboration,
        admission_evidence=admission,
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    return {
        "admission": admission,
        "attestation": attestation,
        "receipt": receipt,
        "checkpoint": checkpoint,
        "fingerprint": manager.fingerprint_sha256,
        "corroboration": corroboration,
        "report": report,
        "package": package,
        "export": export,
    }


def test_portable_reviewer_export_reproduces_all_local_checks(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="VALID")
    export = evidence["export"]

    assert export.reproduction_status == "SELF_CONTAINED_EVIDENCE_INPUTS"
    assert export.monitor_verification_status == "UNVERIFIED"
    assert export.review_status == "HUMAN_REVIEW_REQUIRED"
    assert export.approval_status == "NOT_APPROVED_BY_THIS_BUNDLE"
    assert export.authorization_effect == "NONE"
    assert export.readiness_effect == "NONE"
    assert export.execution_effect_applied is False
    verify_independent_review_export_bundle(export)


def test_export_rejects_tampered_signed_checkpoint(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="CHECKPOINT-TAMPER")
    tampered_checkpoint = copy.deepcopy(evidence["checkpoint"])
    tampered_checkpoint["signature_b64url"] = "tampered-signature"
    tampered = evidence["export"].model_copy(
        update={"checkpoint_bundle": tampered_checkpoint}
    )

    with pytest.raises(
        IndependentReviewExportError,
        match="signed checkpoint corroboration reproduction failed",
    ):
        verify_independent_review_export_bundle(tampered)


def test_export_rejects_wrong_checkpoint_trust_fingerprint(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="WRONG-FINGERPRINT")
    tampered = evidence["export"].model_copy(
        update={"expected_checkpoint_key_fingerprint_sha256": "f" * 64}
    )

    with pytest.raises(
        IndependentReviewExportError,
        match="signed checkpoint corroboration reproduction failed",
    ):
        verify_independent_review_export_bundle(tampered)


def test_export_rejects_raw_admission_tamper(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="ADMISSION-TAMPER")
    tampered_admission = evidence["admission"].model_copy(
        update={"action_id": "ACTION-FORGED"}
    )
    tampered = evidence["export"].model_copy(
        update={"admission_evidence": tampered_admission}
    )

    with pytest.raises(
        IndependentReviewExportError,
        match="independent evaluator reproduction failed",
    ):
        verify_independent_review_export_bundle(tampered)


def test_export_rejects_individually_valid_report_substitution(
    tmp_path,
    echo_checkpoint_key,
):
    first = _evidence_set(tmp_path, echo_checkpoint_key, suffix="SOURCE-A")
    second = _evidence_set(tmp_path, echo_checkpoint_key, suffix="SOURCE-B")
    substituted = first["export"].model_copy(
        update={"evaluator_report": second["report"]}
    )

    with pytest.raises(
        IndependentReviewExportError,
        match="reproduced evaluator report does not match supplied report",
    ):
        verify_independent_review_export_bundle(substituted)


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("reproduction_status", "UNVERIFIED_INPUTS"),
        ("monitor_verification_status", "VERIFIED"),
        ("review_status", "APPROVED"),
        ("approval_status", "APPROVED"),
        ("authorization_effect", "ALLOW"),
        ("readiness_effect", "READY"),
        ("execution_effect_applied", True),
        ("claims_boundary", "all guarantees established"),
    ],
)
def test_export_verifier_rejects_boundary_tampering(
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
    tampered = evidence["export"].model_copy(update={field_name: unsafe_value})

    with pytest.raises(IndependentReviewExportError, match="invariant mismatch"):
        verify_independent_review_export_bundle(tampered)


def test_export_digest_detects_digest_substitution(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="DIGEST")
    tampered = evidence["export"].model_copy(
        update={"bundle_digest_sha256": "f" * 64}
    )

    with pytest.raises(IndependentReviewExportError, match="bundle digest mismatch"):
        verify_independent_review_export_bundle(tampered)


def test_export_cannot_validate_as_fasa_readiness_or_consumption(
    tmp_path,
    echo_checkpoint_key,
):
    evidence = _evidence_set(tmp_path, echo_checkpoint_key, suffix="NONAUTHORITY")
    payload = evidence["export"].model_dump(mode="json")

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(payload)
    with pytest.raises(ValidationError):
        FASAExecutionReadinessConsumption.model_validate(payload)
