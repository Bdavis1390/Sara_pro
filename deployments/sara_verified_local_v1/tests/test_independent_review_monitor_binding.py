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


NOW = datetime(2026, 9, 12, 2, 20, tzinfo=timezone.utc)


def _build_bound_evidence(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    action_id = "ACTION-MONITOR-BINDING"
    model_id = "MODEL-MONITOR-BINDING"
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
        evaluation_id="EVAL-MONITOR-BINDING",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id="POLICY-MONITOR-BINDING")
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
        observation_id="OBS-MONITOR-BINDING",
        action_id=action_id,
        monitor_id="OVERWATCH-CORROBORATED",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW + timedelta(seconds=1),
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    attestation = OverwatchAttestationContract(
        attestation_id="ATTEST-MONITOR-BINDING",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce="nonce-monitor-binding-0001",
    )

    sara = DurableStore(tmp_path / "sara-monitor-binding")
    echo = EchoEventStore((tmp_path / "echo-monitor-binding").resolve())
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
        key_id="ECHO-CHECKPOINT-MONITOR-BINDING-V1",
    )
    checkpoint = manager.create_checkpoint()
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    return admission, attestation, receipt, corroboration


def test_corroboration_digest_binds_claimed_monitor_identity(
    tmp_path,
    echo_checkpoint_key,
):
    _admission, _attestation, _receipt, corroboration = _build_bound_evidence(
        tmp_path,
        echo_checkpoint_key,
    )
    assert corroboration.monitor_id == "OVERWATCH-CORROBORATED"

    tampered = corroboration.model_copy(update={"monitor_id": "OVERWATCH-SUBSTITUTED"})
    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="corroboration digest mismatch",
    ):
        verify_independent_checkpoint_corroboration(tampered)


def test_review_package_rejects_self_consistent_monitor_substitution(
    tmp_path,
    echo_checkpoint_key,
):
    admission, attestation, receipt, corroboration = _build_bound_evidence(
        tmp_path,
        echo_checkpoint_key,
    )

    substituted_observation = attestation.observation.model_copy(
        update={"monitor_id": "OVERWATCH-SUBSTITUTED"}
    )
    substituted_attestation = OverwatchAttestationContract(
        attestation_id="ATTEST-MONITOR-SUBSTITUTED",
        observation=substituted_observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce="nonce-monitor-binding-0002",
    )
    substituted_report = build_independent_evaluator_report(
        review_id="INDEPENDENT-REVIEW-MONITOR-SUBSTITUTION",
        admission_evidence=admission,
        overwatch_attestation=substituted_attestation,
        overwatch_provenance=receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )

    assert substituted_report.overwatch_monitor_id == "OVERWATCH-SUBSTITUTED"
    assert corroboration.monitor_id == "OVERWATCH-CORROBORATED"
    with pytest.raises(
        IndependentReviewPackageError,
        match="monitor binding mismatch",
    ):
        build_independent_review_package(
            evaluator_report=substituted_report,
            checkpoint_corroboration=corroboration,
        )
