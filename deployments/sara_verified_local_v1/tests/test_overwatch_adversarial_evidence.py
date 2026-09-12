from __future__ import annotations

import copy
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_checkpoint import EchoCheckpointError, EchoCheckpointManager
from worldshepherd_sara.echo_checkpoint_verify import (
    EchoCheckpointVerificationError,
    verify_bundle,
)
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.overwatch_attestation_contract import OverwatchAttestationContract
from worldshepherd_sara.overwatch_provenance import (
    OverwatchProvenanceError,
    deliver_overwatch_intent_provenance,
    queue_overwatch_intent_provenance,
)
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchDisposition,
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 1, 5, tzinfo=timezone.utc)


def _observation(
    observation_id: str,
    *,
    signals: tuple[OverwatchSignal, ...] = (OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    telemetry_complete: bool = True,
    monitor_heartbeat_present: bool = True,
) -> OverwatchObservation:
    return OverwatchObservation(
        observation_id=observation_id,
        action_id=f"ACTION-{observation_id}",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        telemetry_complete=telemetry_complete,
        monitor_heartbeat_present=monitor_heartbeat_present,
        signals=signals,
    )


def _record_and_deliver(
    tmp_path,
    observation: OverwatchObservation,
):
    sara_store = DurableStore(tmp_path / "sara")
    echo_store = EchoEventStore((tmp_path / "echo").resolve())
    decision = classify_overwatch_observation(observation)
    intent = record_overwatch_containment_intent(
        sara_store,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )
    receipt = deliver_overwatch_intent_provenance(
        sara_store,
        echo_store,
        intent=intent,
    )
    return sara_store, echo_store, decision, intent, receipt


def test_tampered_containment_digest_cannot_enter_provenance(tmp_path):
    store = DurableStore(tmp_path / "sara")
    decision = classify_overwatch_observation(_observation("OBS-TAMPER-DIGEST"))
    intent = record_overwatch_containment_intent(
        store,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )
    tampered = intent.model_copy(
        update={"decision_digest_sha256": "f" * 64}
    )

    with pytest.raises(OverwatchProvenanceError, match="binding mismatch"):
        queue_overwatch_intent_provenance(store, intent=tampered)


def test_tampered_overwatch_checkpoint_bundle_fails_verification(
    tmp_path,
    echo_checkpoint_key,
):
    key, _path = echo_checkpoint_key
    _sara, echo, _decision, _intent, receipt = _record_and_deliver(
        tmp_path,
        _observation("OBS-TAMPER-CHECKPOINT"),
    )
    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-OVERWATCH-ADVERSARIAL-V1",
    )
    bundle = manager.create_checkpoint()
    assert any(
        item["event_id"] == receipt.provenance_event_id
        for item in bundle["manifest"]["events"]
    )

    tampered = copy.deepcopy(bundle)
    for item in tampered["manifest"]["events"]:
        if item["event_id"] == receipt.provenance_event_id:
            item["semantic_sha256"] = "f" * 64
            break

    with pytest.raises(EchoCheckpointVerificationError):
        verify_bundle(tampered, manager.fingerprint_sha256)


def test_deletion_of_checkpointed_overwatch_event_blocks_next_checkpoint(
    tmp_path,
    echo_checkpoint_key,
):
    key, _path = echo_checkpoint_key
    _sara, echo, _decision, _intent, receipt = _record_and_deliver(
        tmp_path,
        _observation("OBS-DELETE-AFTER-CHECKPOINT"),
    )
    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-OVERWATCH-DELETION-V1",
    )
    manager.create_checkpoint()

    connection = sqlite3.connect(echo.db_path)
    try:
        connection.execute(
            "DELETE FROM events WHERE event_id=?",
            (receipt.provenance_event_id,),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        EchoCheckpointError,
        match="deletion or substitution blocks checkpoint creation",
    ):
        manager.create_checkpoint()


@pytest.mark.parametrize(
    ("telemetry_complete", "heartbeat_present", "expected_reason"),
    [
        (False, True, "required monitoring telemetry is incomplete"),
        (True, False, "independent monitor heartbeat is absent"),
    ],
)
def test_monitor_integrity_loss_fails_closed_into_contain_evidence(
    tmp_path,
    echo_checkpoint_key,
    telemetry_complete,
    heartbeat_present,
    expected_reason,
):
    key, _path = echo_checkpoint_key
    observation = _observation(
        f"OBS-INTEGRITY-{telemetry_complete}-{heartbeat_present}",
        signals=(),
        telemetry_complete=telemetry_complete,
        monitor_heartbeat_present=heartbeat_present,
    )
    _sara, echo, decision, intent, receipt = _record_and_deliver(
        tmp_path,
        observation,
    )

    assert decision.disposition == OverwatchDisposition.CONTAIN
    assert expected_reason in decision.reasons
    assert intent.disposition == OverwatchDisposition.CONTAIN
    stored = echo.get(receipt.provenance_event_id)
    assert stored is not None
    assert stored.payload()["disposition"] == OverwatchDisposition.CONTAIN.value
    assert stored.payload()["monitor_identity_authenticated"] is False

    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-OVERWATCH-INTEGRITY-V1",
    )
    bundle = manager.create_checkpoint()
    membership = {
        item["event_id"]: item["semantic_sha256"]
        for item in bundle["manifest"]["events"]
    }
    assert membership[receipt.provenance_event_id] == receipt.echo_semantic_sha256


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("verification_status", "VERIFIED"),
        ("authorization_effect", "ALLOW"),
        ("execution_effect_applied", True),
    ],
)
def test_unverified_attestation_contract_rejects_authority_escalation(
    field_name,
    unsafe_value,
):
    observation = _observation(
        f"OBS-ATTESTATION-{field_name}",
        signals=(),
    )
    payload = {
        "attestation_id": f"ATTEST-{field_name}",
        "observation": observation.model_dump(mode="json"),
        "issued_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(seconds=10)).isoformat(),
        "nonce": "nonce-overwatch-0001",
        field_name: unsafe_value,
    }

    with pytest.raises(ValidationError):
        OverwatchAttestationContract.model_validate(payload)


def test_attestation_contract_cannot_claim_long_lived_monitor_authority():
    observation = _observation("OBS-ATTESTATION-LIFETIME", signals=())

    with pytest.raises(ValidationError, match="lifetime exceeds 30 seconds"):
        OverwatchAttestationContract(
            attestation_id="ATTEST-LONG-LIVED",
            observation=observation,
            issued_at=NOW,
            expires_at=NOW + timedelta(seconds=31),
            nonce="nonce-overwatch-0002",
        )
