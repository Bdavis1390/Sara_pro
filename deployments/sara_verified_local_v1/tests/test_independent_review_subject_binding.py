from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

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
from worldshepherd_sara.independent_checkpoint_corroboration import (
    IndependentCheckpointCorroborationError,
    corroborate_overwatch_checkpoint,
    verify_independent_checkpoint_corroboration,
)
from worldshepherd_sara.independent_evaluator import build_independent_evaluator_report
from worldshepherd_sara.independent_review_package import (
    IndependentReviewPackageError,
    build_independent_review_package,
)
from worldshepherd_sara.overwatch_attestation_contract import OverwatchAttestationContract
from worldshepherd_sara.overwatch_provenance import deliver_overwatch_intent_provenance
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 2, 45, tzinfo=timezone.utc)


def _baseline(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    action_id = "ACTION-SUBJECT-BINDING"
    model_id = "MODEL-SUBJECT-BINDING"
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
        evaluation_id="EVAL-SUBJECT-BINDING",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id="POLICY-SUBJECT-BINDING")
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
        observation_id="OBS-SUBJECT-BINDING",
        action_id=action_id,
        monitor_id="OVERWATCH-SUBJECT-BINDING",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW + timedelta(seconds=1),
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    attestation = OverwatchAttestationContract(
        attestation_id="ATTEST-SUBJECT-BINDING",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce="nonce-subject-binding-0001",
    )

    sara = DurableStore(tmp_path / "sara-subject-binding")
    echo = EchoEventStore((tmp_path / "echo-subject-binding").resolve())
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
        key_id="ECHO-CHECKPOINT-SUBJECT-BINDING-V1",
    )
    checkpoint = manager.create_checkpoint()
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    return admission, attestation, receipt, corroboration


def _substituted_report(
    *,
    admission,
    attestation,
    receipt,
    field_name: str,
    substituted_value: str,
):
    action_id = admission.action_id
    model_id = admission.model_id
    model_version = admission.model_version
    if field_name == "action_id":
        action_id = substituted_value
    elif field_name == "model_id":
        model_id = substituted_value
    elif field_name == "model_version":
        model_version = substituted_value
    else:  # pragma: no cover - parametrization is fixed below
        raise AssertionError(field_name)

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
        evaluation_id=f"EVAL-SUBSTITUTED-{field_name}",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id=f"POLICY-SUBSTITUTED-{field_name}")
    disposition, reasons = evaluate_frontier_action(candidate, registry, policy)
    substituted_admission = build_admission_evidence(
        candidate,
        registry,
        policy,
        disposition,
        reasons,
        assessed_at=NOW,
    )

    substituted_observation = attestation.observation.model_copy(
        update={field_name: substituted_value}
    )
    substituted_attestation = OverwatchAttestationContract(
        attestation_id=f"ATTEST-SUBSTITUTED-{field_name}",
        observation=substituted_observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce=f"nonce-subject-substituted-{field_name}-0001",
    )
    return build_independent_evaluator_report(
        review_id=f"INDEPENDENT-REVIEW-SUBSTITUTED-{field_name}",
        admission_evidence=substituted_admission,
        overwatch_attestation=substituted_attestation,
        overwatch_provenance=receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )


@pytest.mark.parametrize(
    ("field_name", "substituted_value"),
    [
        ("action_id", "ACTION-SUBSTITUTED"),
        ("model_id", "MODEL-SUBSTITUTED"),
        ("model_version", "v2-substituted"),
    ],
)
def test_corroboration_digest_binds_subject_fields(
    tmp_path,
    echo_checkpoint_key,
    field_name,
    substituted_value,
):
    _admission, _attestation, _receipt, corroboration = _baseline(
        tmp_path,
        echo_checkpoint_key,
    )
    tampered = corroboration.model_copy(update={field_name: substituted_value})

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="corroboration digest mismatch",
    ):
        verify_independent_checkpoint_corroboration(tampered)


@pytest.mark.parametrize(
    ("field_name", "substituted_value", "expected_error"),
    [
        ("action_id", "ACTION-SUBSTITUTED", "action binding mismatch"),
        ("model_id", "MODEL-SUBSTITUTED", "model binding mismatch"),
        ("model_version", "v2-substituted", "model-version binding mismatch"),
    ],
)
def test_review_package_rejects_self_consistent_subject_substitution(
    tmp_path,
    echo_checkpoint_key,
    field_name,
    substituted_value,
    expected_error,
):
    admission, attestation, receipt, corroboration = _baseline(
        tmp_path,
        echo_checkpoint_key,
    )
    report = _substituted_report(
        admission=admission,
        attestation=attestation,
        receipt=receipt,
        field_name=field_name,
        substituted_value=substituted_value,
    )

    assert getattr(report, field_name) == substituted_value
    assert getattr(corroboration, field_name) != substituted_value
    with pytest.raises(IndependentReviewPackageError, match=expected_error):
        build_independent_review_package(
            evaluator_report=report,
            checkpoint_corroboration=corroboration,
        )
