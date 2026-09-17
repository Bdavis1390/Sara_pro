from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.registry_monotonic_witness import (
    InMemoryMonotonicWitness,
    RegistryMonotonicWitnessClient,
    RegistryMonotonicWitnessVerifier,
    RegistryWitnessConflict,
    RegistryWitnessCoordinates,
    RegistryWitnessRollbackDetected,
    RegistryWitnessSignatureError,
    RegistryWitnessUnavailable,
    TEST_WITNESS_MODE,
)
from worldshepherd_sara.storage import DurableStore


NAMESPACE = "worldshepherd/sara/registry"
WITNESS_ID = "WS-MAG-1-6-TEST"
KEY_ID = "WS-MAG-1-6-KEY"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _h(character: str) -> str:
    return character * 64


def _fixture():
    private_key = Ed25519PrivateKey.generate()
    transport = InMemoryMonotonicWitness(
        private_key=private_key,
        witness_id=WITNESS_ID,
        key_id=KEY_ID,
        issued_at="2026-09-17T19:30:00+00:00",
    )
    verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            KEY_ID: _b64url(private_key.public_key().public_bytes_raw()),
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=NAMESPACE,
    )
    return private_key, transport, verifier, RegistryMonotonicWitnessClient(
        transport=transport,
        verifier=verifier,
    )


def _status(generation: int, state_root: str, commit_hash: str):
    return {
        "generation": generation,
        "state_root_sha256": state_root,
        "commit_hash": commit_hash,
    }


def test_signed_monotonic_witness_advances_and_verifies_exact_checkpoint():
    _private, transport, verifier, client = _fixture()
    local = _status(7, _h("a"), _h("b"))

    assessment = client.advance_and_verify(local)
    head = transport.read_head(NAMESPACE)

    assert assessment["status"] == "PASS"
    assert assessment["generation"] == 7
    assert assessment["signature_verified"] is True
    assert assessment["monotonic_match"] is True
    assert assessment["external_witnessed"] is False
    assert assessment["independence_verified"] is False
    assert assessment["witness_mode"] == TEST_WITNESS_MODE
    assert head is not None
    assert verifier.verify_receipt(head)["receipt_sha256"] == assessment["witness_receipt_sha256"]


def test_same_generation_same_coordinates_is_idempotent_but_conflict_is_rejected():
    _private, transport, _verifier, _client = _fixture()
    coordinates = RegistryWitnessCoordinates(3, _h("c"), _h("d"))

    first = transport.witness(NAMESPACE, coordinates)
    second = transport.witness(NAMESPACE, coordinates)
    assert second == first

    with pytest.raises(RegistryWitnessConflict, match="conflicting checkpoint"):
        transport.witness(
            NAMESPACE,
            RegistryWitnessCoordinates(3, _h("e"), _h("d")),
        )


def test_witness_refuses_generation_rollback():
    _private, transport, _verifier, _client = _fixture()
    transport.witness(NAMESPACE, RegistryWitnessCoordinates(4, _h("1"), _h("2")))

    with pytest.raises(RegistryWitnessRollbackDetected, match="lower than its monotonic head"):
        transport.witness(
            NAMESPACE,
            RegistryWitnessCoordinates(3, _h("3"), _h("4")),
        )


def test_newer_signed_witness_detects_coherent_local_registry_and_journal_rollback(tmp_path):
    _private, _transport, verifier, client = _fixture()
    store = DurableStore(tmp_path)
    store.patch_registry({"SECURITY_STATE": "OLD"})
    old_registry = store.registry_path.read_bytes()
    old_journal = store.registry_checkpoint_path.read_bytes()

    store.patch_registry({"SECURITY_STATE": "NEW"})
    new_status = store.checkpoint_status()
    assert new_status["generation"] > 0
    client.advance_and_verify(new_status)

    # Roll back both local files coherently. MAG-1.5 local verification alone
    # accepts this because its entire local history was restored together.
    store.registry_path.write_bytes(old_registry)
    store.registry_checkpoint_path.write_bytes(old_journal)
    os.chmod(store.registry_path, 0o600)
    os.chmod(store.registry_checkpoint_path, 0o600)

    reopened = DurableStore(tmp_path)
    assert reopened.get_registry()["SECURITY_STATE"] == "OLD"

    witness_head = client.transport.read_head(NAMESPACE)
    assert witness_head is not None
    with pytest.raises(
        RegistryWitnessRollbackDetected,
        match="older than signed monotonic witness head",
    ):
        verifier.assess_local_checkpoint(reopened.checkpoint_status(), witness_head)


def test_same_generation_different_local_state_conflicts_with_signed_witness():
    _private, transport, verifier, _client = _fixture()
    receipt = transport.witness(
        NAMESPACE,
        RegistryWitnessCoordinates(9, _h("a"), _h("b")),
    )

    with pytest.raises(RegistryWitnessConflict, match="same generation"):
        verifier.assess_local_checkpoint(_status(9, _h("c"), _h("b")), receipt)


def test_older_witness_is_reported_as_not_covering_newer_local_generation():
    _private, transport, verifier, _client = _fixture()
    receipt = transport.witness(
        NAMESPACE,
        RegistryWitnessCoordinates(2, _h("a"), _h("b")),
    )

    result = verifier.assess_local_checkpoint(
        _status(3, _h("c"), _h("d")),
        receipt,
    )

    assert result["status"] == "NEEDS_WITNESS_ADVANCE"
    assert result["generation"] == 3
    assert result["witness_generation"] == 2
    assert result["external_witnessed"] is False


def test_tampered_receipt_and_unpinned_key_fail_signature_verification():
    _private, transport, verifier, _client = _fixture()
    receipt = transport.witness(
        NAMESPACE,
        RegistryWitnessCoordinates(1, _h("a"), _h("b")),
    )

    tampered = dict(receipt)
    tampered["state_root_sha256"] = _h("c")
    with pytest.raises(RegistryWitnessSignatureError, match="signature verification failed"):
        verifier.verify_receipt(tampered)

    other_private = Ed25519PrivateKey.generate()
    wrong_verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            "OTHER-KEY": _b64url(other_private.public_key().public_bytes_raw()),
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=NAMESPACE,
    )
    with pytest.raises(RegistryWitnessSignatureError, match="not pinned"):
        wrong_verifier.verify_receipt(receipt)


def test_test_only_witness_never_earns_external_or_independence_credit():
    _private, transport, verifier, client = _fixture()
    local = _status(5, _h("e"), _h("f"))
    client.advance_and_verify(local)

    assessment = verifier.assess_local_checkpoint(
        local,
        transport.read_head(NAMESPACE),
    )

    assert assessment["witness_mode"] == TEST_WITNESS_MODE
    assert assessment["external_witnessed"] is False
    assert assessment["independence_verified"] is False
    assert "Deployment independence is not inferred" in assessment["claims_boundary"]


class _UnavailableTransport:
    witness_mode = "REMOTE_WITNESS"

    def read_head(self, namespace):
        raise OSError("offline")

    def witness(self, namespace, coordinates):
        raise OSError("offline")


def test_required_witness_head_fails_closed_when_transport_is_unavailable():
    private_key = Ed25519PrivateKey.generate()
    verifier = RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            KEY_ID: _b64url(private_key.public_key().public_bytes_raw()),
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=NAMESPACE,
    )
    client = RegistryMonotonicWitnessClient(
        transport=_UnavailableTransport(),
        verifier=verifier,
    )

    with pytest.raises(RegistryWitnessUnavailable, match="unable to read"):
        client.check(_status(1, _h("a"), _h("b")), require_head=True)
