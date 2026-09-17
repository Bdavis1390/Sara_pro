from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    EventOutboxError,
    queue_event_outbox_patch,
)
from worldshepherd_sara.mag1_gate import Mag1Disposition
from worldshepherd_sara.mag1_prime_binding import PRIME_MAG1_ACTION
from worldshepherd_sara.mag1_prime_transition import (
    PRIME_CUSTODY_REGISTRY_KEY,
    PRIME_MAG1_TRANSITION_EVENT,
    PrimeMag1TransitionDisposition,
    PrimeMag1TransitionError,
    execute_prime_requalification_transition,
    get_prime_custody_record,
    prime_custody_registry_patch,
)
from worldshepherd_sara.prime_configuration_custody import (
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
    REQUALIFICATION_CHECKS,
)
from worldshepherd_sara.prime_sentinel_authorization import (
    PRIME_SENTINEL_AUTHZ_REGISTRY_KEY,
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    canonical_authorization_message,
    verified_authorization_registry_patch,
)
from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.trajectory_guard import TrajectoryState


NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keypair():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            "PS-MAG12": _b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def _assertion(
    private: Ed25519PrivateKey,
    *,
    authorization_id: str = "AUTH-MAG12-001",
    prime_id: str = "PRIME-MAG12",
    target_environment: PrimeEnvironment = PrimeEnvironment.SPACE,
) -> PrimeSentinelAuthorizationAssertion:
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-MAG12",
        authorization_id=authorization_id,
        prime_id=prime_id,
        target_environment=target_environment,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
        nonce="nonce-mag12-0123456789",
        signature_b64url=_b64url(b"0" * 64),
    )
    return assertion.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_authorization_message(assertion))
            )
        }
    )


def _custody() -> PrimeConfigurationCustodyRecord:
    return PrimeConfigurationCustodyRecord(
        prime_id="PRIME-MAG12",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )


def _pack(**overrides) -> PrimeMissionPackEvidence:
    values = dict(
        pack_id="SPACE-PACK-MAG12",
        target_environment=PrimeEnvironment.SPACE,
        authenticated=True,
        compatible_with_prime=True,
        target_environment_qualification_valid=True,
    )
    values.update(overrides)
    return PrimeMissionPackEvidence(**values)


def _candidate(**overrides) -> AutonomousActionCandidate:
    values = dict(
        action_id="ACT-MAG12",
        action_type=PRIME_MAG1_ACTION,
        confidence=1.0,
        requested_authority=1,
        reversible=True,
    )
    values.update(overrides)
    return AutonomousActionCandidate(**values)


def _policy(**overrides) -> AutonomyPolicy:
    values = dict(
        policy_id="POL-MAG12",
        allowed_auto_action_types=[PRIME_MAG1_ACTION],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )
    values.update(overrides)
    return AutonomyPolicy(**values)


def _trajectory() -> TrajectoryState:
    return TrajectoryState(
        trajectory_id="TRJ-MAG12",
        originating_human_request_hash="sha256:request",
        root_authority="PRIME_SENTINEL",
    )


def _initialized_store(tmp_path):
    private, verifier = _keypair()
    assertion = _assertion(private)
    verified = verifier.verify(assertion, now=NOW)
    store = DurableStore(tmp_path)
    store.patch_registry(verified_authorization_registry_patch({}, verified))
    store.patch_registry(
        prime_custody_registry_patch(store.get_registry(), _custody())
    )
    store.patch_registry({"UNRELATED_STATE": {"preserve": True}})
    return store, private, verifier, assertion


def _execute(store, verifier, assertion, **overrides):
    values = dict(
        assertion=assertion,
        verifier=verifier,
        pack=_pack(),
        candidate=_candidate(),
        autonomy_policy=_policy(),
        trajectory_state=_trajectory(),
        trajectory_action_id="ACT-MAG12",
        now=NOW,
    )
    values.update(overrides)
    return execute_prime_requalification_transition(store, **values)


def test_success_atomically_consumes_authorization_releases_custody_and_queues_two_events(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    result = _execute(store, verifier, assertion)

    assert result.disposition == PrimeMag1TransitionDisposition.APPLIED
    assert result.transition_id is not None
    assert result.mag1_decision.disposition == Mag1Disposition.AUTO_ELIGIBLE
    assert result.mag1_event_id is not None
    assert result.transition_event_id is not None

    registry = store.get_registry()
    auth = registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]
    assert auth["status"] == "CONSUMED"
    assert auth["consumed_transition_id"] == result.transition_id

    custody = get_prime_custody_record(registry, prime_id=assertion.prime_id)
    assert custody.state == PrimeCustodyState.READY
    assert custody.requalification_release_authorization_id is None
    assert custody.requalification_release_target_environment is None
    assert custody.requalification_release_key_id is None

    outbox = registry[EVENT_OUTBOX_REGISTRY_KEY]
    assert set((result.mag1_event_id, result.transition_event_id)).issubset(outbox)
    assert outbox[result.transition_event_id]["event"] == PRIME_MAG1_TRANSITION_EVENT
    assert registry["UNRELATED_STATE"] == {"preserve": True}


def test_mag1_human_review_records_decision_but_does_not_consume_or_release(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    result = _execute(
        store,
        verifier,
        assertion,
        autonomy_policy=_policy(allowed_auto_action_types=[]),
    )

    assert result.disposition == PrimeMag1TransitionDisposition.NOT_APPLIED
    assert result.mag1_decision.disposition == Mag1Disposition.HUMAN_REVIEW_REQUIRED
    assert result.transition_id is None

    registry = store.get_registry()
    assert registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "VERIFIED"
    assert get_prime_custody_record(
        registry, prime_id=assertion.prime_id
    ).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert result.mag1_event_id in registry[EVENT_OUTBOX_REGISTRY_KEY]
    assert result.transition_event_id is None


def test_invalid_pack_aborts_without_consuming_authority_or_changing_registry(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    before = store.get_registry()

    with pytest.raises(PrimeMag1TransitionError, match="custody release gate"):
        _execute(
            store,
            verifier,
            assertion,
            pack=_pack(authenticated=False),
        )

    assert store.get_registry() == before


def test_signed_target_environment_must_match_pack_before_transition(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    before = store.get_registry()

    with pytest.raises(PrimeMag1TransitionError, match="target environment"):
        _execute(
            store,
            verifier,
            assertion,
            pack=_pack(target_environment=PrimeEnvironment.AERO),
        )

    assert store.get_registry() == before


def test_existing_conflicting_custody_authorization_cannot_be_silently_overwritten(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    registry = store.get_registry()
    conflicting = _custody().model_copy(
        update={"requalification_release_authorization_id": "AUTH-OTHER"}
    )
    store.patch_registry(prime_custody_registry_patch(registry, conflicting))
    before = store.get_registry()

    with pytest.raises(PrimeMag1TransitionError, match="conflicts"):
        _execute(store, verifier, assertion)

    assert store.get_registry() == before


def test_tampered_signature_aborts_before_any_registry_write(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    before = store.get_registry()
    raw = base64.urlsafe_b64decode(assertion.signature_b64url + "==")
    tampered_raw = bytes([raw[0] ^ 1]) + raw[1:]
    tampered = assertion.model_copy(update={"signature_b64url": _b64url(tampered_raw)})

    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        _execute(store, verifier, tampered)

    assert store.get_registry() == before


def test_action_identity_substitution_is_rejected_before_transaction(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    before = store.get_registry()

    with pytest.raises(PrimeMag1TransitionError, match="action_id"):
        _execute(
            store,
            verifier,
            assertion,
            candidate=_candidate(action_id="ACT-DIFFERENT"),
        )

    assert store.get_registry() == before


def test_replay_after_success_cannot_reapply_transition(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    first = _execute(store, verifier, assertion)
    after_first = store.get_registry()

    with pytest.raises(PrimeMag1TransitionError, match="not quarantined"):
        _execute(store, verifier, assertion)

    assert store.get_registry() == after_first
    assert first.disposition == PrimeMag1TransitionDisposition.APPLIED


def test_outbox_capacity_failure_rolls_back_consumption_and_custody_release(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)
    working = store.get_registry()
    for index in range(31):
        patch, _ = queue_event_outbox_patch(
            working,
            event="fixture_event",
            actor="TEST",
            payload={"index": index},
            event_id=f"FIXTURE-{index:02d}",
        )
        working.update(patch)
    store.patch_registry({EVENT_OUTBOX_REGISTRY_KEY: working[EVENT_OUTBOX_REGISTRY_KEY]})
    before = store.get_registry()

    with pytest.raises(EventOutboxError, match="capacity"):
        _execute(store, verifier, assertion)

    after = store.get_registry()
    assert after == before
    assert after[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "VERIFIED"
    assert get_prime_custody_record(
        after, prime_id=assertion.prime_id
    ).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert len(after[EVENT_OUTBOX_REGISTRY_KEY]) == 31


def test_same_store_concurrent_requalification_serializes_to_one_success(tmp_path):
    store, _private, verifier, assertion = _initialized_store(tmp_path)

    def attempt():
        try:
            return _execute(store, verifier, assertion)
        except (PrimeMag1TransitionError, PrimeSentinelAuthorizationError) as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: attempt(), range(2)))

    applied = [
        result
        for result in results
        if not isinstance(result, Exception)
        and result.disposition == PrimeMag1TransitionDisposition.APPLIED
    ]
    failures = [result for result in results if isinstance(result, Exception)]
    assert len(applied) == 1
    assert len(failures) == 1

    registry = store.get_registry()
    assert registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "CONSUMED"
    assert get_prime_custody_record(
        registry, prime_id=assertion.prime_id
    ).state == PrimeCustodyState.READY


def test_custody_registry_round_trip_is_identity_bound(tmp_path):
    store = DurableStore(tmp_path)
    record = _custody()
    store.patch_registry(prime_custody_registry_patch({}, record))
    registry = store.get_registry()
    assert PRIME_CUSTODY_REGISTRY_KEY in registry
    assert get_prime_custody_record(registry, prime_id=record.prime_id) == record
