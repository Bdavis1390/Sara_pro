from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.mag1_prime_binding import PRIME_MAG1_ACTION
from worldshepherd_sara.mag1_prime_transition import (
    OVERWATCH_CONTAINMENT_BLOCK_EVENT,
    PrimeMag1TransitionDisposition,
    execute_prime_requalification_transition,
    get_prime_custody_record,
    prime_custody_registry_patch,
)
from worldshepherd_sara.overwatch_containment import (
    OverwatchContainmentDirective,
    OverwatchContainmentError,
    OverwatchContainmentState,
    OverwatchContainmentVerifier,
    OverwatchDirectiveSignature,
    canonical_overwatch_message,
)
from worldshepherd_sara.overwatch_containment_store import (
    apply_overwatch_containment_directive,
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
from worldshepherd_sara.registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryMonotonicWitnessVerifier,
    build_signed_witness_receipt,
    coordinates_from_checkpoint_status,
)
from worldshepherd_sara.registry_witness_gate import RegistryWitnessPrecondition
from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.trajectory_guard import TrajectoryState


NOW = datetime(2026, 9, 17, 19, 30, tzinfo=timezone.utc)
WITNESS_ID = "WITNESS-OW-UNIT"
WITNESS_KEY_ID = "WITNESS-OW-UNIT-KEY"
WITNESS_NAMESPACE = "worldshepherd/sara/registry"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _prime_authority():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={"PS-OW": _b64url(private.public_key().public_bytes_raw())}
    )
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-OW",
        authorization_id="AUTH-OW-001",
        prime_id="PRIME-OW-TRANSITION",
        target_environment=PrimeEnvironment.SPACE,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=5),
        nonce="prime-overwatch-nonce-0001",
        signature_b64url=_b64url(b"0" * 64),
    )
    assertion = assertion.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_authorization_message(assertion))
            )
        }
    )
    return verifier, assertion


def _overwatch_authority():
    keys = {
        "OW-A": Ed25519PrivateKey.generate(),
        "OW-B": Ed25519PrivateKey.generate(),
        "OW-C": Ed25519PrivateKey.generate(),
    }
    verifier = OverwatchContainmentVerifier(
        public_keys_b64url={
            key_id: _b64url(private.public_key().public_bytes_raw())
            for key_id, private in keys.items()
        },
        hold_quorum=1,
        clear_quorum=2,
    )
    return keys, verifier


def _overwatch_directive(
    keys,
    *,
    state: OverwatchContainmentState,
    signer_ids: tuple[str, ...],
    sequence: int,
    previous: str | None,
) -> OverwatchContainmentDirective:
    draft = OverwatchContainmentDirective(
        directive_id=f"OW-TRANSITION-{state.value}-{sequence}",
        prime_id="PRIME-OW-TRANSITION",
        target_environment=PrimeEnvironment.SPACE,
        state=state,
        sequence=sequence,
        previous_directive_sha256=previous,
        reason_code="SENSOR.ANOMALY" if state == OverwatchContainmentState.HOLD else "HUMAN.RECOVERY.APPROVED",
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(minutes=5),
        nonce=f"overwatch-transition-{state.value.lower()}-{sequence:04d}",
        signatures=[
            OverwatchDirectiveSignature(key_id=key_id, signature_b64url="placeholder")
            for key_id in signer_ids
        ],
    )
    message = canonical_overwatch_message(draft)
    return draft.model_copy(
        update={
            "signatures": [
                OverwatchDirectiveSignature(
                    key_id=key_id,
                    signature_b64url=_b64url(keys[key_id].sign(message)),
                )
                for key_id in signer_ids
            ]
        }
    )


def _store(tmp_path):
    prime_verifier, assertion = _prime_authority()
    verified = prime_verifier.verify(assertion, now=NOW)
    store = DurableStore(tmp_path)
    store.patch_registry(verified_authorization_registry_patch({}, verified))
    custody = PrimeConfigurationCustodyRecord(
        prime_id=assertion.prime_id,
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )
    store.patch_registry(prime_custody_registry_patch(store.get_registry(), custody))
    return store, prime_verifier, assertion


def _signed_remote_witness(store: DurableStore):
    private = Ed25519PrivateKey.generate()
    coordinates = coordinates_from_checkpoint_status(store.checkpoint_status())
    receipt = build_signed_witness_receipt(
        private_key=private,
        witness_id=WITNESS_ID,
        key_id=WITNESS_KEY_ID,
        namespace=WITNESS_NAMESPACE,
        coordinates=coordinates,
        issued_at=NOW.isoformat(),
        witness_mode=REMOTE_WITNESS_MODE,
    )
    witness_verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            WITNESS_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=WITNESS_NAMESPACE,
    )
    precondition = RegistryWitnessPrecondition(
        generation=coordinates.generation,
        state_root_sha256=coordinates.state_root_sha256,
        commit_hash=coordinates.commit_hash,
        witness_id=WITNESS_ID,
        witness_mode=REMOTE_WITNESS_MODE,
        witness_receipt_sha256=str(receipt["receipt_sha256"]),
        witness_receipt_json=json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ),
    )
    return precondition, witness_verifier


def _execute(store, prime_verifier, assertion, *, overwatch_verifier=None):
    precondition, witness_verifier = _signed_remote_witness(store)
    return execute_prime_requalification_transition(
        store,
        assertion=assertion,
        verifier=prime_verifier,
        pack=PrimeMissionPackEvidence(
            pack_id="SPACE-PACK-OW",
            target_environment=PrimeEnvironment.SPACE,
            authenticated=True,
            compatible_with_prime=True,
            target_environment_qualification_valid=True,
        ),
        candidate=AutonomousActionCandidate(
            action_id="ACT-OW",
            action_type=PRIME_MAG1_ACTION,
            confidence=1.0,
            requested_authority=1,
            reversible=True,
        ),
        autonomy_policy=AutonomyPolicy(
            policy_id="POL-OW",
            allowed_auto_action_types=[PRIME_MAG1_ACTION],
            minimum_auto_confidence=0.99,
            maximum_auto_authority=1,
        ),
        trajectory_state=TrajectoryState(
            trajectory_id="TRJ-OW",
            originating_human_request_hash="sha256:request",
            root_authority="PRIME_SENTINEL",
        ),
        trajectory_action_id="ACT-OW",
        overwatch_verifier=overwatch_verifier,
        registry_witness_precondition=precondition,
        registry_witness_verifier=witness_verifier,
        now=NOW,
    )


def test_signed_hold_is_a_precommit_veto_not_posthoc_telemetry(tmp_path):
    store, prime_verifier, assertion = _store(tmp_path)
    keys, overwatch_verifier = _overwatch_authority()
    hold = _overwatch_directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
        sequence=1,
        previous=None,
    )
    status = apply_overwatch_containment_directive(
        store,
        directive=hold,
        verifier=overwatch_verifier,
        now=NOW,
    )
    assert status.active is True

    result = _execute(
        store,
        prime_verifier,
        assertion,
        overwatch_verifier=overwatch_verifier,
    )

    assert result.disposition == PrimeMag1TransitionDisposition.CONTAINED
    assert result.transition_id is None
    assert result.transition_event_id is None
    assert result.overwatch_directive_id == hold.directive_id
    assert result.overwatch_containment_event_id is not None

    registry = store.get_registry()
    assert registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "VERIFIED"
    assert get_prime_custody_record(
        registry,
        prime_id=assertion.prime_id,
    ).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    block = registry[EVENT_OUTBOX_REGISTRY_KEY][result.overwatch_containment_event_id]
    assert block["event"] == OVERWATCH_CONTAINMENT_BLOCK_EVENT


def test_dual_signed_clear_reenables_transition_and_is_bound_into_evidence(tmp_path):
    store, prime_verifier, assertion = _store(tmp_path)
    keys, overwatch_verifier = _overwatch_authority()
    hold = _overwatch_directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
        sequence=1,
        previous=None,
    )
    hold_status = apply_overwatch_containment_directive(
        store,
        directive=hold,
        verifier=overwatch_verifier,
        now=NOW,
    )
    clear = _overwatch_directive(
        keys,
        state=OverwatchContainmentState.CLEAR,
        signer_ids=("OW-B", "OW-C"),
        sequence=2,
        previous=hold_status.directive_sha256,
    )
    clear_status = apply_overwatch_containment_directive(
        store,
        directive=clear,
        verifier=overwatch_verifier,
        now=NOW,
    )
    assert clear_status.active is False
    assert clear_status.sequence == 2

    result = _execute(
        store,
        prime_verifier,
        assertion,
        overwatch_verifier=overwatch_verifier,
    )

    assert result.disposition == PrimeMag1TransitionDisposition.APPLIED
    assert result.transition_id is not None
    assert result.registry_witness_receipt_sha256 is not None
    assert result.overwatch_directive_id == clear.directive_id
    assert result.overwatch_directive_sha256 == clear_status.directive_sha256
    assert result.overwatch_sequence == 2
    registry = store.get_registry()
    assert registry[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "CONSUMED"
    assert get_prime_custody_record(
        registry,
        prime_id=assertion.prime_id,
    ).state == PrimeCustodyState.READY
    transition = registry[EVENT_OUTBOX_REGISTRY_KEY][result.transition_event_id]
    assert transition["payload"]["overwatch_state"] == "CLEAR"
    assert transition["payload"]["overwatch_sequence"] == 2
    assert transition["payload"]["overwatch_directive_sha256"] == clear_status.directive_sha256
    assert transition["payload"]["registry_witness_required"] is True


def test_existing_containment_state_without_verifier_fails_closed(tmp_path):
    store, prime_verifier, assertion = _store(tmp_path)
    keys, overwatch_verifier = _overwatch_authority()
    hold = _overwatch_directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
        sequence=1,
        previous=None,
    )
    apply_overwatch_containment_directive(
        store,
        directive=hold,
        verifier=overwatch_verifier,
        now=NOW,
    )
    before = store.get_registry()

    with pytest.raises(OverwatchContainmentError, match="verifier is required"):
        _execute(store, prime_verifier, assertion, overwatch_verifier=None)

    assert store.get_registry() == before


def test_tampered_persisted_hold_fails_closed_without_consumption_or_release(tmp_path):
    store, prime_verifier, assertion = _store(tmp_path)
    keys, overwatch_verifier = _overwatch_authority()
    hold = _overwatch_directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
        sequence=1,
        previous=None,
    )
    apply_overwatch_containment_directive(
        store,
        directive=hold,
        verifier=overwatch_verifier,
        now=NOW,
    )
    registry = store.get_registry()
    registry["OVERWATCH_CONTAINMENT"][assertion.prime_id]["directive"]["reason_code"] = "TAMPERED.HOLD"
    store.patch_registry({"OVERWATCH_CONTAINMENT": registry["OVERWATCH_CONTAINMENT"]})
    before = store.get_registry()

    with pytest.raises(OverwatchContainmentError, match="signature"):
        _execute(
            store,
            prime_verifier,
            assertion,
            overwatch_verifier=overwatch_verifier,
        )

    after = store.get_registry()
    assert after == before
    assert after[PRIME_SENTINEL_AUTHZ_REGISTRY_KEY][assertion.authorization_id]["status"] == "VERIFIED"
    assert get_prime_custody_record(after, prime_id=assertion.prime_id).state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
