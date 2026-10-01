from __future__ import annotations

import os
import stat
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.ws_soe import (
    Intent,
    ReplayError,
    authorize_intent,
    canonical_sha256,
)
from worldshepherd_sara.ws_soe_v01b import (
    AuthoritySignatureError,
    DecisionAuthorityVerifier,
    LocalEd25519DecisionAuthoritySigner,
)
from worldshepherd_sara.ws_soe_v01c import (
    EXTERNAL_ACTION,
    EXTERNAL_TARGET,
    CoordinatorStateError,
    ExecutionStoreError,
    ExternalEffectUncertain,
    ExternalOperationState,
    ExternalReconciliationCoordinator,
    ExternalRequestConflict,
    InjectedCoordinatorCrash,
    MockExternalCounterService,
)


def _intent(now: datetime, *, suffix: str = "001") -> Intent:
    return Intent(
        intent_id=f"intent-v01c-{suffix}",
        action=EXTERNAL_ACTION,
        target=EXTERNAL_TARGET,
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=2),
        nonce=f"nonce-v01c-{suffix}",
    )


def _signing_fixture(intent: Intent, now: datetime):
    signer = LocalEd25519DecisionAuthoritySigner(
        private_key=Ed25519PrivateKey.generate(),
        authority="prime-v01c-test-authority",
        key_id="prime-v01c-key-01",
    )
    decision = authorize_intent(
        intent,
        decision_id=f"decision-{intent.intent_id}",
        authority=signer.authority,
        decided_at=now - timedelta(milliseconds=500),
    )
    signature = signer.sign_decision(decision)
    verifier = DecisionAuthorityVerifier.from_raw_public_key(
        authority=signer.authority,
        key_id=signer.key_id,
        public_key_bytes=signer.public_key_bytes(),
    )
    return signer, decision, signature, verifier


def _service(tmp_path) -> MockExternalCounterService:
    return MockExternalCounterService((tmp_path / "external").resolve())


def _coordinator(tmp_path, verifier, service) -> ExternalReconciliationCoordinator:
    return ExternalReconciliationCoordinator(
        (tmp_path / "coordinator").resolve(),
        verifier,
        service,
    )


def test_positive_external_effect_is_observed_reconciled_and_sealed(tmp_path):
    now = datetime(2026, 10, 1, 17, 0, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    observation = coordinator.execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-v01c-positive",
    )

    assert observation.before == {"counter": 41}
    assert observation.after == {"counter": 42}
    assert observation.result["reconciled"] is True
    assert service.counter_value() == 42
    assert service.effect_count() == 1

    record = coordinator.get_record(canonical_sha256(intent))
    assert record is not None
    assert record.state == ExternalOperationState.SEALED.value
    assert record.observation_hash == canonical_sha256(observation)

    states = [row.to_state for row in coordinator.transition_history(canonical_sha256(intent))]
    assert states == [
        ExternalOperationState.PREPARED.value,
        ExternalOperationState.DISPATCHING.value,
        ExternalOperationState.EFFECT_OBSERVED.value,
        ExternalOperationState.RECONCILED.value,
        ExternalOperationState.SEALED.value,
    ]


def test_commit_before_ack_becomes_uncertain_then_reconciles_without_duplicate(tmp_path):
    now = datetime(2026, 10, 1, 17, 1, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(ExternalEffectUncertain, match="reconciliation is required"):
        coordinator.execute(
            intent,
            decision,
            signature,
            now=now,
            observation_id="obs-never-returned",
            fault="after_external_commit_before_ack",
        )

    intent_hash = canonical_sha256(intent)
    record = coordinator.get_record(intent_hash)
    assert record is not None
    assert record.state == ExternalOperationState.UNCERTAIN.value
    assert service.counter_value() == 42
    assert service.effect_count() == 1

    reopened = _coordinator(tmp_path, verifier, service)
    result = reopened.reconcile(
        intent_hash,
        now=now + timedelta(seconds=1),
        observation_id="obs-v01c-reconciled",
    )

    assert result.effect_found is True
    assert result.state == ExternalOperationState.SEALED
    assert result.observation is not None
    assert result.observation.before == {"counter": 41}
    assert result.observation.after == {"counter": 42}
    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_crash_after_ack_before_local_record_recovers_from_dispatching(tmp_path):
    now = datetime(2026, 10, 1, 17, 2, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(InjectedCoordinatorCrash, match="after external acknowledgement"):
        coordinator.execute(
            intent,
            decision,
            signature,
            now=now,
            observation_id="obs-lost-locally",
            fault="after_external_ack_before_local_record",
        )

    intent_hash = canonical_sha256(intent)
    record = coordinator.get_record(intent_hash)
    assert record is not None
    assert record.state == ExternalOperationState.DISPATCHING.value
    assert record.observation_json is None
    assert service.counter_value() == 42
    assert service.effect_count() == 1

    reopened = _coordinator(tmp_path, verifier, service)
    result = reopened.reconcile(
        intent_hash,
        now=now + timedelta(seconds=1),
        observation_id="obs-recovered-after-ack",
    )
    assert result.effect_found is True
    assert result.state == ExternalOperationState.SEALED
    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_crash_before_external_call_requires_negative_reconciliation_before_redispatch(tmp_path):
    now = datetime(2026, 10, 1, 17, 3, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(InjectedCoordinatorCrash, match="before external service call"):
        coordinator.execute(
            intent,
            decision,
            signature,
            now=now,
            observation_id="obs-not-used",
            fault="crash_before_external_call",
        )

    intent_hash = canonical_sha256(intent)
    assert service.counter_value() == 41
    assert service.effect_count() == 0
    assert coordinator.get_record(intent_hash).state == ExternalOperationState.DISPATCHING.value

    with pytest.raises(CoordinatorStateError, match="NO_EFFECT_CONFIRMED"):
        coordinator.redispatch_after_no_effect(
            intent_hash,
            now=now + timedelta(milliseconds=100),
            observation_id="obs-too-early",
        )

    result = coordinator.reconcile(
        intent_hash,
        now=now + timedelta(seconds=1),
        observation_id="obs-no-effect",
    )
    assert result.effect_found is False
    assert result.state == ExternalOperationState.NO_EFFECT_CONFIRMED
    assert service.counter_value() == 41
    assert service.effect_count() == 0

    observation = coordinator.redispatch_after_no_effect(
        intent_hash,
        now=now + timedelta(seconds=2),
        observation_id="obs-explicit-redispatch",
    )
    assert observation.before == {"counter": 41}
    assert observation.after == {"counter": 42}
    assert service.counter_value() == 42
    assert service.effect_count() == 1
    assert coordinator.get_record(intent_hash).state == ExternalOperationState.SEALED.value


def test_redispatch_ack_loss_returns_to_uncertain_and_reconciles(tmp_path):
    now = datetime(2026, 10, 1, 17, 4, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(InjectedCoordinatorCrash):
        coordinator.execute(
            intent,
            decision,
            signature,
            now=now,
            observation_id="unused",
            fault="crash_before_external_call",
        )
    intent_hash = canonical_sha256(intent)
    coordinator.reconcile(
        intent_hash,
        now=now + timedelta(seconds=1),
        observation_id="unused-negative",
    )

    with pytest.raises(ExternalEffectUncertain):
        coordinator.redispatch_after_no_effect(
            intent_hash,
            now=now + timedelta(seconds=2),
            observation_id="unused-lost-ack",
            fault="after_commit_before_ack",
        )

    assert coordinator.get_record(intent_hash).state == ExternalOperationState.UNCERTAIN.value
    assert service.counter_value() == 42
    assert service.effect_count() == 1

    result = coordinator.reconcile(
        intent_hash,
        now=now + timedelta(seconds=3),
        observation_id="obs-after-redispatch-reconcile",
    )
    assert result.effect_found is True
    assert result.state == ExternalOperationState.SEALED
    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_replay_after_seal_is_rejected_before_second_external_effect(tmp_path):
    now = datetime(2026, 10, 1, 17, 5, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    coordinator.execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-first",
    )
    with pytest.raises(ReplayError, match="durable external-operation"):
        coordinator.execute(
            intent,
            decision,
            signature,
            now=now + timedelta(seconds=1),
            observation_id="obs-replay",
        )

    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_external_service_identical_idempotent_redelivery_returns_first_effect(tmp_path):
    now = datetime(2026, 10, 1, 17, 6, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    coordinator.execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-first",
        fault=None,
    )
    record = coordinator.get_record(canonical_sha256(intent))
    assert record is not None

    from worldshepherd_sara.ws_soe_v01c import ExternalRequest

    request = ExternalRequest.model_validate_json(record.request_json)
    first = service.lookup(request.idempotency_key)
    duplicate = service.apply(request, now=now + timedelta(seconds=10))

    assert first is not None
    assert duplicate == first
    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_external_service_rejects_idempotency_key_rebound_to_other_request_bytes(tmp_path):
    now = datetime(2026, 10, 1, 17, 7, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)
    coordinator.execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-first",
    )
    record = coordinator.get_record(canonical_sha256(intent))
    assert record is not None

    from worldshepherd_sara.ws_soe_v01c import ExternalRequest

    request = ExternalRequest.model_validate_json(record.request_json)
    conflicting = request.model_copy(update={"intent_hash": "sha256:" + "0" * 64})
    with pytest.raises(ExternalRequestConflict, match="different request bytes"):
        service.apply(conflicting, now=now + timedelta(seconds=1))

    assert service.counter_value() == 42
    assert service.effect_count() == 1


def test_forged_authority_signature_is_rejected_before_local_or_external_effect(tmp_path):
    now = datetime(2026, 10, 1, 17, 8, 0, tzinfo=UTC)
    intent = _intent(now)
    signer, decision, _, verifier = _signing_fixture(intent, now)
    attacker = LocalEd25519DecisionAuthoritySigner(
        private_key=Ed25519PrivateKey.generate(),
        authority=signer.authority,
        key_id=signer.key_id,
    )
    forged = attacker.sign_decision(decision)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(AuthoritySignatureError, match="verification failed"):
        coordinator.execute(
            intent,
            decision,
            forged,
            now=now,
            observation_id="obs-forged",
        )

    assert coordinator.get_record(canonical_sha256(intent)) is None
    assert service.counter_value() == 41
    assert service.effect_count() == 0


def test_decision_mutation_after_signing_is_rejected_before_prepare(tmp_path):
    now = datetime(2026, 10, 1, 17, 9, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    tampered = decision.model_copy(update={"reason": "mutated after authority signature"})
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    with pytest.raises(AuthoritySignatureError, match="exact decision"):
        coordinator.execute(
            intent,
            tampered,
            signature,
            now=now,
            observation_id="obs-tampered",
        )

    assert coordinator.get_record(canonical_sha256(intent)) is None
    assert service.counter_value() == 41


def test_coordinator_and_verifier_expose_no_signing_method_or_private_key(tmp_path):
    now = datetime(2026, 10, 1, 17, 10, 0, tzinfo=UTC)
    intent = _intent(now)
    _, _, _, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    assert not hasattr(verifier, "sign_decision")
    assert not hasattr(verifier, "private_key")
    assert not hasattr(coordinator, "sign_decision")
    assert not hasattr(coordinator, "private_key")


def test_v01c_databases_are_owner_only_regular_files(tmp_path):
    now = datetime(2026, 10, 1, 17, 11, 0, tzinfo=UTC)
    intent = _intent(now)
    _, _, _, verifier = _signing_fixture(intent, now)
    service = _service(tmp_path)
    coordinator = _coordinator(tmp_path, verifier, service)

    for path in (service.db_path, coordinator.db_path):
        status = path.lstat()
        assert stat.S_ISREG(status.st_mode)
        assert status.st_uid == os.geteuid()
        assert stat.S_IMODE(status.st_mode) == 0o600


def test_relative_data_paths_are_rejected(tmp_path, monkeypatch):
    now = datetime(2026, 10, 1, 17, 12, 0, tzinfo=UTC)
    intent = _intent(now)
    _, _, _, verifier = _signing_fixture(intent, now)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ExecutionStoreError, match="absolute"):
        MockExternalCounterService("relative-external")

    service = MockExternalCounterService((tmp_path / "external").resolve())
    with pytest.raises(ExecutionStoreError, match="absolute"):
        ExternalReconciliationCoordinator("relative-local", verifier, service)
