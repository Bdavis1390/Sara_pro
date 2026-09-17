from __future__ import annotations

import base64
import multiprocessing as mp
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.mag1_prime_binding import PRIME_MAG1_ACTION
from worldshepherd_sara.mag1_prime_transition import (
    PrimeMag1TransitionDisposition,
    execute_prime_requalification_transition,
    get_prime_custody_record,
    prime_custody_registry_patch,
)
from worldshepherd_sara.overwatch_containment import (
    OverwatchContainmentDirective,
    OverwatchContainmentState,
    OverwatchContainmentVerifier,
    OverwatchDirectiveSignature,
    canonical_overwatch_message,
    verified_containment_registry_patch,
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
    PrimeSentinelVerifier,
    canonical_authorization_message,
    verified_authorization_registry_patch,
)
from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.trajectory_guard import TrajectoryState


NOW = datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc)
PRIME_ID = "PRIME-OW-RACE"
AUTHORIZATION_ID = "AUTH-OW-RACE-001"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _public_b64(private: Ed25519PrivateKey) -> str:
    return _b64url(private.public_key().public_bytes_raw())


def _build_prime_authority():
    private = Ed25519PrivateKey.generate()
    public_b64 = _public_b64(private)
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-RACE",
        authorization_id=AUTHORIZATION_ID,
        prime_id=PRIME_ID,
        target_environment=PrimeEnvironment.SPACE,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
        nonce="prime-overwatch-race-nonce-0001",
        signature_b64url=_b64url(b"0" * 64),
    )
    assertion = assertion.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_authorization_message(assertion))
            )
        }
    )
    return public_b64, assertion


def _build_overwatch_hold():
    private = Ed25519PrivateKey.generate()
    public_b64 = _public_b64(private)
    draft = OverwatchContainmentDirective(
        directive_id="OW-RACE-HOLD-1",
        prime_id=PRIME_ID,
        target_environment=PrimeEnvironment.SPACE,
        state=OverwatchContainmentState.HOLD,
        sequence=1,
        previous_directive_sha256=None,
        reason_code="CONCURRENT.RACE.HOLD",
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(minutes=5),
        nonce="overwatch-race-hold-nonce-0001",
        signatures=[
            OverwatchDirectiveSignature(
                key_id="OW-RACE",
                signature_b64url="placeholder",
            )
        ],
    )
    signature = private.sign(canonical_overwatch_message(draft))
    directive = draft.model_copy(
        update={
            "signatures": [
                OverwatchDirectiveSignature(
                    key_id="OW-RACE",
                    signature_b64url=_b64url(signature),
                )
            ]
        }
    )
    return public_b64, directive


def _install_hold_while_owning_transaction_lock(
    data_dir: str,
    directive_json: dict,
    overwatch_public_b64: str,
    hold_lock_acquired,
    release_hold,
    result_queue,
) -> None:
    try:
        store = DurableStore(data_dir)
        verifier = OverwatchContainmentVerifier(
            public_keys_b64url={"OW-RACE": overwatch_public_b64},
            hold_quorum=1,
            clear_quorum=2,
        )
        directive = OverwatchContainmentDirective.model_validate(directive_json)

        def operation(registry):
            # transact_registry has already acquired both the in-process RLock
            # and, on supported POSIX runtimes, the process-visible flock.
            patch = verified_containment_registry_patch(
                registry,
                directive,
                verifier=verifier,
                now=NOW,
            )
            hold_lock_acquired.set()
            if not release_hold.wait(timeout=15):
                raise RuntimeError("parent did not release HOLD transaction")
            return patch, directive.directive_id

        directive_id = store.transact_registry(operation)
        result_queue.put(("hold", "ok", directive_id))
    except BaseException as exc:  # pragma: no cover - surfaced in parent.
        result_queue.put(("hold", "error", f"{type(exc).__name__}: {exc}"))


def _attempt_transition_after_hold_owns_lock(
    data_dir: str,
    assertion_json: dict,
    prime_public_b64: str,
    overwatch_public_b64: str,
    transition_started,
    result_queue,
) -> None:
    try:
        store = DurableStore(data_dir)
        prime_verifier = PrimeSentinelVerifier(
            public_keys_b64url={"PS-RACE": prime_public_b64}
        )
        overwatch_verifier = OverwatchContainmentVerifier(
            public_keys_b64url={"OW-RACE": overwatch_public_b64},
            hold_quorum=1,
            clear_quorum=2,
        )
        assertion = PrimeSentinelAuthorizationAssertion.model_validate(assertion_json)
        transition_started.set()
        result = execute_prime_requalification_transition(
            store,
            assertion=assertion,
            verifier=prime_verifier,
            pack=PrimeMissionPackEvidence(
                pack_id="SPACE-PACK-RACE",
                target_environment=PrimeEnvironment.SPACE,
                authenticated=True,
                compatible_with_prime=True,
                target_environment_qualification_valid=True,
            ),
            candidate=AutonomousActionCandidate(
                action_id="ACT-RACE",
                action_type=PRIME_MAG1_ACTION,
                confidence=1.0,
                requested_authority=1,
                reversible=True,
            ),
            autonomy_policy=AutonomyPolicy(
                policy_id="POL-RACE",
                allowed_auto_action_types=[PRIME_MAG1_ACTION],
                minimum_auto_confidence=0.99,
                maximum_auto_authority=1,
            ),
            trajectory_state=TrajectoryState(
                trajectory_id="TRJ-RACE",
                originating_human_request_hash="sha256:race-request",
                root_authority="PRIME_SENTINEL",
            ),
            trajectory_action_id="ACT-RACE",
            overwatch_verifier=overwatch_verifier,
            now=NOW,
        )
        registry = store.get_registry()
        custody = get_prime_custody_record(registry, prime_id=PRIME_ID)
        auth_status = registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTHORIZATION_ID]["status"]
        result_queue.put(
            (
                "transition",
                "ok",
                {
                    "disposition": result.disposition.value,
                    "auth_status": auth_status,
                    "custody_state": custody.state.value,
                    "directive_id": result.overwatch_directive_id,
                },
            )
        )
    except BaseException as exc:  # pragma: no cover - surfaced in parent.
        result_queue.put(
            ("transition", "error", f"{type(exc).__name__}: {exc}")
        )


def test_overwatch_hold_wins_serialized_process_race_against_prime_release(tmp_path):
    parent_store = DurableStore(tmp_path)
    if not parent_store.registry_cross_process_lock_supported:
        pytest.skip("POSIX flock is unavailable on this runtime")

    prime_public_b64, assertion = _build_prime_authority()
    prime_verifier = PrimeSentinelVerifier(
        public_keys_b64url={"PS-RACE": prime_public_b64}
    )
    verified = prime_verifier.verify(assertion, now=NOW)
    parent_store.patch_registry(verified_authorization_registry_patch({}, verified))
    custody = PrimeConfigurationCustodyRecord(
        prime_id=PRIME_ID,
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )
    parent_store.patch_registry(
        prime_custody_registry_patch(parent_store.get_registry(), custody)
    )

    overwatch_public_b64, hold = _build_overwatch_hold()
    ctx = mp.get_context("spawn")
    hold_lock_acquired = ctx.Event()
    release_hold = ctx.Event()
    transition_started = ctx.Event()
    result_queue = ctx.Queue()

    hold_process = ctx.Process(
        target=_install_hold_while_owning_transaction_lock,
        args=(
            str(tmp_path),
            hold.model_dump(mode="json"),
            overwatch_public_b64,
            hold_lock_acquired,
            release_hold,
            result_queue,
        ),
    )
    hold_process.start()
    assert hold_lock_acquired.wait(timeout=15), "HOLD worker never acquired transaction lock"

    transition_process = ctx.Process(
        target=_attempt_transition_after_hold_owns_lock,
        args=(
            str(tmp_path),
            assertion.model_dump(mode="json"),
            prime_public_b64,
            overwatch_public_b64,
            transition_started,
            result_queue,
        ),
    )
    transition_process.start()
    assert transition_started.wait(timeout=15), "transition worker never started"

    # The transition worker has started while the HOLD worker still owns the
    # process-visible registry transaction lock. Releasing HOLD now forces the
    # transition's subsequent registry read to observe the committed directive.
    release_hold.set()

    results = [result_queue.get(timeout=30) for _ in range(2)]
    hold_process.join(timeout=30)
    transition_process.join(timeout=30)
    assert hold_process.exitcode == 0
    assert transition_process.exitcode == 0

    by_role = {role: (status, payload) for role, status, payload in results}
    assert by_role["hold"] == ("ok", hold.directive_id)
    transition_status, transition_payload = by_role["transition"]
    assert transition_status == "ok", transition_payload
    assert transition_payload["disposition"] == PrimeMag1TransitionDisposition.CONTAINED.value
    assert transition_payload["auth_status"] == "VERIFIED"
    assert transition_payload["custody_state"] == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION.value
    assert transition_payload["directive_id"] == hold.directive_id

    final_registry = parent_store.get_registry()
    assert final_registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][AUTHORIZATION_ID]["status"] == "VERIFIED"
    assert get_prime_custody_record(
        final_registry,
        prime_id=PRIME_ID,
    ).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert final_registry["OVERWATCH_CONTAINMENT"][PRIME_ID]["directive_id"] == hold.directive_id
