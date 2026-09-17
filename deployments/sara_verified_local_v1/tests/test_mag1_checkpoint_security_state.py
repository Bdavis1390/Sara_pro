from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.overwatch_containment import (
    OverwatchContainmentDirective,
    OverwatchContainmentState,
    OverwatchContainmentVerifier,
    OverwatchDirectiveSignature,
    canonical_overwatch_message,
)
from worldshepherd_sara.overwatch_containment_store import (
    apply_overwatch_containment_directive,
)
from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment
from worldshepherd_sara.registry_checkpoint import RegistryCheckpointIntegrityError
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 17, 21, 30, tzinfo=timezone.utc)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _signed_hold():
    private = Ed25519PrivateKey.generate()
    verifier = OverwatchContainmentVerifier(
        public_keys_b64url={
            "OW-CHECKPOINT": _b64url(private.public_key().public_bytes_raw())
        },
        hold_quorum=1,
        clear_quorum=2,
    )
    draft = OverwatchContainmentDirective(
        directive_id="OW-CHECKPOINT-HOLD-1",
        prime_id="PRIME-CHECKPOINT",
        target_environment=PrimeEnvironment.SPACE,
        state=OverwatchContainmentState.HOLD,
        sequence=1,
        previous_directive_sha256=None,
        reason_code="ROLLBACK.PROTECTION.TEST",
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(minutes=5),
        nonce="overwatch-checkpoint-nonce-0001",
        signatures=[
            OverwatchDirectiveSignature(
                key_id="OW-CHECKPOINT",
                signature_b64url="placeholder",
            )
        ],
    )
    signature = private.sign(canonical_overwatch_message(draft))
    directive = draft.model_copy(
        update={
            "signatures": [
                OverwatchDirectiveSignature(
                    key_id="OW-CHECKPOINT",
                    signature_b64url=_b64url(signature),
                )
            ]
        }
    )
    return verifier, directive


def test_restoring_registry_to_pre_hold_state_is_detected_while_checkpoint_history_remains(tmp_path):
    store = DurableStore(tmp_path)
    before_hold_registry = store.registry_path.read_bytes()
    verifier, hold = _signed_hold()

    status = apply_overwatch_containment_directive(
        store,
        directive=hold,
        verifier=verifier,
        now=NOW,
    )
    assert status.active is True
    assert store.get_registry()["OVERWATCH_CONTAINMENT"][hold.prime_id]["state"] == "HOLD"

    # Simulate restoration of registry.json from a backup taken before HOLD,
    # while the independently persisted checkpoint journal remains current.
    store.registry_path.write_bytes(before_hold_registry)
    os.chmod(store.registry_path, 0o600)

    with pytest.raises(RegistryCheckpointIntegrityError, match="rollback|tamper"):
        DurableStore(tmp_path)


def test_restoring_pre_consumption_authorization_namespace_is_detected(tmp_path):
    store = DurableStore(tmp_path)
    store.patch_registry(
        {
            "PRIME_SENTINEL_AUTHORIZATIONS": {
                "AUTH-ROLLBACK-1": {
                    "status": "VERIFIED",
                    "prime_id": "PRIME-CHECKPOINT",
                }
            }
        }
    )
    before_consumption_registry = store.registry_path.read_bytes()

    store.patch_registry(
        {
            "PRIME_SENTINEL_AUTHORIZATIONS": {
                "AUTH-ROLLBACK-1": {
                    "status": "CONSUMED",
                    "prime_id": "PRIME-CHECKPOINT",
                    "consumed_transition_id": "TRANSITION-1",
                }
            }
        }
    )
    assert (
        store.get_registry()["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-ROLLBACK-1"]["status"]
        == "CONSUMED"
    )

    store.registry_path.write_bytes(before_consumption_registry)
    os.chmod(store.registry_path, 0o600)

    with pytest.raises(RegistryCheckpointIntegrityError, match="rollback|tamper"):
        DurableStore(tmp_path)


def test_restoring_older_journal_while_registry_remains_newer_is_detected(tmp_path):
    store = DurableStore(tmp_path)
    store.patch_registry({"STATE": "ONE"})
    old_journal = store.registry_checkpoint_path.read_bytes()
    store.patch_registry({"STATE": "TWO"})
    assert store.get_registry()["STATE"] == "TWO"

    store.registry_checkpoint_path.write_bytes(old_journal)
    os.chmod(store.registry_checkpoint_path, 0o600)

    with pytest.raises(RegistryCheckpointIntegrityError, match="checkpoint|rollback|mismatch"):
        DurableStore(tmp_path)


def test_coordinated_registry_and_journal_rollback_is_explicitly_outside_local_detection_boundary(tmp_path):
    store = DurableStore(tmp_path)
    store.patch_registry({"STATE": "OLD"})
    old_registry = store.registry_path.read_bytes()
    old_journal = store.registry_checkpoint_path.read_bytes()

    store.patch_registry({"STATE": "NEW"})
    assert store.get_registry()["STATE"] == "NEW"

    # This intentionally captures the local-only assurance boundary. If an
    # actor can roll back BOTH files coherently, there is no independent local
    # monotonic witness left from which to prove that the newer generation ever
    # existed. A later external witness/anchor must close that stronger threat.
    store.registry_path.write_bytes(old_registry)
    store.registry_checkpoint_path.write_bytes(old_journal)
    os.chmod(store.registry_path, 0o600)
    os.chmod(store.registry_checkpoint_path, 0o600)

    reopened = DurableStore(tmp_path)
    assert reopened.get_registry()["STATE"] == "OLD"
    receipt = reopened.checkpoint_status()
    assert receipt["external_witnessed"] is False
