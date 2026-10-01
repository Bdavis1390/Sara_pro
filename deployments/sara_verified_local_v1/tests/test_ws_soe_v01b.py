from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.ws_soe import (
    ConformanceStatus,
    Intent,
    ReplayError,
    assess_conformance,
    authorize_intent,
    canonical_sha256,
    make_evidence_receipt,
)
from worldshepherd_sara.ws_soe_v01b import (
    AuthoritySignatureError,
    DecisionAuthorityVerifier,
    DurableDemoCounterExecutor,
    DurableExecutionStore,
    ExecutionStoreError,
    LocalEd25519DecisionAuthoritySigner,
)


def _intent(now: datetime, *, suffix: str = "001") -> Intent:
    return Intent(
        intent_id=f"intent-v01b-{suffix}",
        action="demo.counter.increment",
        target="demo.counter",
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        nonce=f"nonce-v01b-{suffix}",
    )


def _signing_fixture(intent: Intent, now: datetime):
    signer = LocalEd25519DecisionAuthoritySigner(
        private_key=Ed25519PrivateKey.generate(),
        authority="prime-test-authority",
        key_id="prime-test-key-01",
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


def _store(tmp_path) -> DurableExecutionStore:
    return DurableExecutionStore((tmp_path / "ws-soe-v01b").resolve())


def test_signed_durable_counter_41_to_42_and_conformance_match(tmp_path):
    now = datetime(2026, 10, 1, 14, 0, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    store = _store(tmp_path)
    executor = DurableDemoCounterExecutor(store, verifier)

    observation = executor.execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-v01b-001",
    )

    assert observation.before == {"counter": 41}
    assert observation.after == {"counter": 42}
    assert store.counter_value() == 42
    assert store.execution_count() == 1

    receipt = make_evidence_receipt(
        intent,
        observation,
        receipt_id="receipt-v01b-001",
        emitted_at=now + timedelta(milliseconds=1),
    )
    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=1),
    )
    assert assessment.status == ConformanceStatus.MATCH

    record = store.get_execution(canonical_sha256(intent))
    assert record is not None
    assert record.before_counter == 41
    assert record.after_counter == 42
    assert record.decision_hash == canonical_sha256(decision)
    assert record.signature_hash == canonical_sha256(signature)
    assert record.observation_hash == canonical_sha256(observation)
    assert json.loads(record.decision_json)["decision_id"] == decision.decision_id
    assert json.loads(record.signature_json)["key_id"] == signature.key_id
    assert json.loads(record.observation_json)["observation_id"] == observation.observation_id


def test_replay_persists_across_store_and_executor_reopen(tmp_path):
    now = datetime(2026, 10, 1, 14, 1, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    data_dir = (tmp_path / "ws-soe-v01b").resolve()

    first_store = DurableExecutionStore(data_dir)
    DurableDemoCounterExecutor(first_store, verifier).execute(
        intent,
        decision,
        signature,
        now=now,
        observation_id="obs-first",
    )

    reopened_store = DurableExecutionStore(data_dir)
    reopened_executor = DurableDemoCounterExecutor(reopened_store, verifier)
    with pytest.raises(ReplayError, match="durably consumed"):
        reopened_executor.execute(
            intent,
            decision,
            signature,
            now=now + timedelta(seconds=1),
            observation_id="obs-replay",
        )

    assert reopened_store.counter_value() == 42
    assert reopened_store.execution_count() == 1


def test_transaction_rolls_back_state_and_replay_marker_on_mid_commit_failure(tmp_path):
    class CrashAfterStateUpdate(DurableDemoCounterExecutor):
        def _after_state_update(self, connection):
            raise RuntimeError("injected crash before execution record")

    now = datetime(2026, 10, 1, 14, 2, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    store = _store(tmp_path)

    with pytest.raises(RuntimeError, match="injected crash"):
        CrashAfterStateUpdate(store, verifier).execute(
            intent,
            decision,
            signature,
            now=now,
            observation_id="obs-crash",
        )

    assert store.counter_value() == 41
    assert store.execution_count() == 0
    assert store.get_execution(canonical_sha256(intent)) is None

    observation = DurableDemoCounterExecutor(store, verifier).execute(
        intent,
        decision,
        signature,
        now=now + timedelta(milliseconds=1),
        observation_id="obs-after-recovery",
    )
    assert observation.after == {"counter": 42}
    assert store.execution_count() == 1


def test_forged_signature_is_rejected_before_side_effect(tmp_path):
    now = datetime(2026, 10, 1, 14, 3, 0, tzinfo=UTC)
    intent = _intent(now)
    signer, decision, _, verifier = _signing_fixture(intent, now)
    attacker = LocalEd25519DecisionAuthoritySigner(
        private_key=Ed25519PrivateKey.generate(),
        authority=signer.authority,
        key_id=signer.key_id,
    )
    forged = attacker.sign_decision(decision)
    store = _store(tmp_path)

    with pytest.raises(AuthoritySignatureError, match="verification failed"):
        DurableDemoCounterExecutor(store, verifier).execute(
            intent,
            decision,
            forged,
            now=now,
            observation_id="obs-forged",
        )

    assert store.counter_value() == 41
    assert store.execution_count() == 0


def test_decision_mutation_after_signing_is_rejected(tmp_path):
    now = datetime(2026, 10, 1, 14, 4, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    tampered = decision.model_copy(update={"reason": "tampered after signing"})
    store = _store(tmp_path)

    with pytest.raises(AuthoritySignatureError, match="exact decision"):
        DurableDemoCounterExecutor(store, verifier).execute(
            intent,
            tampered,
            signature,
            now=now,
            observation_id="obs-tampered-decision",
        )

    assert store.counter_value() == 41
    assert store.execution_count() == 0


def test_signer_refuses_authority_substitution():
    now = datetime(2026, 10, 1, 14, 5, 0, tzinfo=UTC)
    intent = _intent(now)
    signer = LocalEd25519DecisionAuthoritySigner(
        private_key=Ed25519PrivateKey.generate(),
        authority="prime-authority-a",
        key_id="prime-key-a",
    )
    decision = authorize_intent(
        intent,
        decision_id="decision-authority-substitution",
        authority="prime-authority-b",
        decided_at=now - timedelta(milliseconds=500),
    )

    with pytest.raises(AuthoritySignatureError, match="does not match"):
        signer.sign_decision(decision)


def test_key_id_substitution_is_rejected(tmp_path):
    now = datetime(2026, 10, 1, 14, 6, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    substituted = signature.model_copy(update={"key_id": "prime-test-key-evil"})
    store = _store(tmp_path)

    with pytest.raises(AuthoritySignatureError, match="key_id"):
        DurableDemoCounterExecutor(store, verifier).execute(
            intent,
            decision,
            substituted,
            now=now,
            observation_id="obs-key-substitution",
        )

    assert store.counter_value() == 41


def test_executor_and_verifier_expose_no_signing_method(tmp_path):
    now = datetime(2026, 10, 1, 14, 7, 0, tzinfo=UTC)
    intent = _intent(now)
    _, _, _, verifier = _signing_fixture(intent, now)
    executor = DurableDemoCounterExecutor(_store(tmp_path), verifier)

    assert not hasattr(verifier, "sign_decision")
    assert not hasattr(executor, "sign_decision")
    assert not hasattr(verifier, "private_key")
    assert not hasattr(executor, "private_key")


def test_observation_id_collision_rolls_back_second_state_change(tmp_path):
    now = datetime(2026, 10, 1, 14, 8, 0, tzinfo=UTC)
    store = _store(tmp_path)

    intent_a = _intent(now, suffix="a")
    signer, decision_a, signature_a, verifier = _signing_fixture(intent_a, now)
    executor = DurableDemoCounterExecutor(store, verifier)
    executor.execute(
        intent_a,
        decision_a,
        signature_a,
        now=now,
        observation_id="obs-collision",
    )
    assert store.counter_value() == 42

    intent_b = _intent(now + timedelta(seconds=1), suffix="b")
    decision_b = authorize_intent(
        intent_b,
        decision_id="decision-v01b-b",
        authority=signer.authority,
        decided_at=now + timedelta(milliseconds=500),
    )
    signature_b = signer.sign_decision(decision_b)

    with pytest.raises(ExecutionStoreError, match="conflicts"):
        executor.execute(
            intent_b,
            decision_b,
            signature_b,
            now=now + timedelta(seconds=1),
            observation_id="obs-collision",
        )

    assert store.counter_value() == 42
    assert store.execution_count() == 1
    assert store.get_execution(canonical_sha256(intent_b)) is None


def test_concurrent_same_intent_produces_one_commit_and_one_replay(tmp_path):
    now = datetime(2026, 10, 1, 14, 9, 0, tzinfo=UTC)
    intent = _intent(now)
    _, decision, signature, verifier = _signing_fixture(intent, now)
    data_dir = (tmp_path / "ws-soe-v01b").resolve()
    DurableExecutionStore(data_dir)

    def worker(observation_id: str) -> str:
        store = DurableExecutionStore(data_dir)
        executor = DurableDemoCounterExecutor(store, verifier)
        try:
            executor.execute(
                intent,
                decision,
                signature,
                now=now,
                observation_id=observation_id,
            )
            return "COMMITTED"
        except ReplayError:
            return "REPLAY"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(worker, ["obs-race-a", "obs-race-b"]))

    reopened = DurableExecutionStore(data_dir)
    assert outcomes == ["COMMITTED", "REPLAY"]
    assert reopened.counter_value() == 42
    assert reopened.execution_count() == 1


def test_database_permissions_are_owner_only(tmp_path):
    store = _store(tmp_path)
    assert store.db_path.stat().st_mode & 0o777 == 0o600


def test_relative_execution_store_path_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ExecutionStoreError, match="must be absolute"):
        DurableExecutionStore("relative-store")
