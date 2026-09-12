from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.fasa_runtime_gate import (
    FASAEchoExecutionReadiness,
    FASAExecutionReadinessConsumption,
)
from worldshepherd_sara.independent_checkpoint_corroboration import (
    IndependentCheckpointCorroborationError,
    corroborate_overwatch_checkpoint,
    verify_independent_checkpoint_corroboration,
)
from worldshepherd_sara.overwatch_attestation_contract import (
    OverwatchAttestationContract,
)
from worldshepherd_sara.overwatch_provenance import (
    OverwatchProvenanceReceipt,
    deliver_overwatch_intent_provenance,
)
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 1, 50, tzinfo=timezone.utc)


def _attestation(observation: OverwatchObservation) -> OverwatchAttestationContract:
    return OverwatchAttestationContract(
        attestation_id=f"ATTEST-{observation.observation_id}",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce=f"nonce-{observation.observation_id}-0001",
    )


def _observation(suffix: str) -> OverwatchObservation:
    return OverwatchObservation(
        observation_id=f"OBS-CORROBORATE-{suffix}",
        action_id=f"ACTION-CORROBORATE-{suffix}",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-CORROBORATE-1",
        model_version="v1",
        observed_at=NOW,
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )


def _deliver(tmp_path, observation: OverwatchObservation, *, name: str):
    sara = DurableStore(tmp_path / f"sara-{name}")
    echo = EchoEventStore((tmp_path / f"echo-{name}").resolve())
    decision = classify_overwatch_observation(observation)
    intent = record_overwatch_containment_intent(
        sara,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )
    receipt = deliver_overwatch_intent_provenance(
        sara,
        echo,
        intent=intent,
    )
    return echo, receipt


def _bundle(tmp_path, echo_checkpoint_key, *, suffix: str = "A"):
    key, _path = echo_checkpoint_key
    observation = _observation(suffix)
    echo, receipt = _deliver(tmp_path, observation, name=suffix)
    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-INDEPENDENT-CORROBORATION-V1",
    )
    bundle = manager.create_checkpoint()
    return observation, receipt, manager, bundle


def test_valid_signed_checkpoint_corroboration_is_evidence_only(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
    )
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=_attestation(observation),
        overwatch_provenance=receipt,
        checkpoint_bundle=bundle,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )

    assert corroboration.observation_id == observation.observation_id
    assert corroboration.provenance_event_id == receipt.provenance_event_id
    assert corroboration.echo_semantic_sha256 == receipt.echo_semantic_sha256
    assert corroboration.decision_recomputed is True
    assert corroboration.checkpoint_signature_verified is True
    assert corroboration.checkpoint_membership_verified is True
    assert corroboration.monitor_verification_status == "UNVERIFIED"
    assert corroboration.authorization_effect == "NONE"
    assert corroboration.readiness_effect == "NONE"
    assert corroboration.execution_effect_applied is False
    verify_independent_checkpoint_corroboration(corroboration)


def test_forged_receipt_decision_digest_fails_recomputation(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
    )
    forged = receipt.model_copy(update={"decision_digest_sha256": "f" * 64})

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="decision digest does not match deterministic recomputation",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=_attestation(observation),
            overwatch_provenance=forged,
            checkpoint_bundle=bundle,
            expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
        )


def test_verified_checkpoint_without_receipt_event_fails_membership(
    tmp_path,
    echo_checkpoint_key,
):
    observation_a, receipt_a, _manager_a, _bundle_a = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="MISSING-A",
    )
    _observation_b, _receipt_b, manager_b, bundle_b = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="MISSING-B",
    )

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="provenance event is absent from the verified checkpoint",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=_attestation(observation_a),
            overwatch_provenance=receipt_a,
            checkpoint_bundle=bundle_b,
            expected_checkpoint_key_fingerprint_sha256=manager_b.fingerprint_sha256,
        )


def test_receipt_semantic_digest_substitution_fails_membership(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="SEMANTIC",
    )
    forged = receipt.model_copy(update={"echo_semantic_sha256": "f" * 64})

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="semantic digest does not match OVERWATCH provenance receipt",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=_attestation(observation),
            overwatch_provenance=forged,
            checkpoint_bundle=bundle,
            expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
        )


def test_tampered_checkpoint_fails_cryptographic_verification(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="TAMPER",
    )
    tampered = copy.deepcopy(bundle)
    tampered["manifest"]["checkpoint_id"] = "CHECKPOINT-TAMPERED"

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="signed ECHO checkpoint verification failed",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=_attestation(observation),
            overwatch_provenance=receipt,
            checkpoint_bundle=tampered,
            expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
        )


def test_wrong_checkpoint_trust_fingerprint_fails_closed(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, _manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="FINGERPRINT",
    )

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="signed ECHO checkpoint verification failed",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=_attestation(observation),
            overwatch_provenance=receipt,
            checkpoint_bundle=bundle,
            expected_checkpoint_key_fingerprint_sha256="f" * 64,
        )


def test_continue_observation_cannot_corroborate_containment_provenance(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="CONTINUE",
    )
    continue_observation = observation.model_copy(update={"signals": ()})
    attestation = _attestation(continue_observation)

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="CONTINUE observation cannot support containment-intent provenance",
    ):
        corroborate_overwatch_checkpoint(
            overwatch_attestation=attestation,
            overwatch_provenance=receipt,
            checkpoint_bundle=bundle,
            expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("decision_recomputed", False),
        ("checkpoint_signature_verified", False),
        ("checkpoint_membership_verified", False),
        ("monitor_verification_status", "VERIFIED"),
        ("authorization_effect", "ALLOW"),
        ("readiness_effect", "READY"),
        ("execution_effect_applied", True),
        ("claims_boundary", "all guarantees established"),
    ],
)
def test_corroboration_verifier_rejects_invariant_tampering(
    tmp_path,
    echo_checkpoint_key,
    field_name,
    unsafe_value,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix=f"INVARIANT-{field_name}",
    )
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=_attestation(observation),
        overwatch_provenance=receipt,
        checkpoint_bundle=bundle,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    tampered = corroboration.model_copy(update={field_name: unsafe_value})

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="invariant mismatch",
    ):
        verify_independent_checkpoint_corroboration(tampered)


def test_corroboration_digest_detects_bound_field_tampering(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="DIGEST",
    )
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=_attestation(observation),
        overwatch_provenance=receipt,
        checkpoint_bundle=bundle,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    tampered = corroboration.model_copy(update={"checkpoint_id": "CHECKPOINT-FORGED"})

    with pytest.raises(
        IndependentCheckpointCorroborationError,
        match="corroboration digest mismatch",
    ):
        verify_independent_checkpoint_corroboration(tampered)


def test_corroboration_cannot_validate_as_fasa_readiness_or_consumption(
    tmp_path,
    echo_checkpoint_key,
):
    observation, receipt, manager, bundle = _bundle(
        tmp_path,
        echo_checkpoint_key,
        suffix="NONAUTHORITY",
    )
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=_attestation(observation),
        overwatch_provenance=receipt,
        checkpoint_bundle=bundle,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    payload = corroboration.model_dump(mode="json")

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(payload)
    with pytest.raises(ValidationError):
        FASAExecutionReadinessConsumption.model_validate(payload)
