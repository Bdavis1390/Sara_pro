from __future__ import annotations

import hashlib
import hmac

import pytest

from worldshepherd_sara.checkpoint_quorum_certificate import (
    build_checkpoint_quorum_certificate,
    export_checkpoint_quorum_certificate,
    import_checkpoint_quorum_certificate,
    verify_checkpoint_quorum_certificate,
)
from worldshepherd_sara.checkpoint_witness import (
    build_witness_quorum_policy,
    create_witness_receipt,
)
from worldshepherd_sara.snapshot_lineage import (
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
)


SECRETS = {
    "witness-a": b"certificate-test-a",
    "witness-b": b"certificate-test-b",
    "witness-c": b"certificate-test-c",
}


def _checkpoint():
    revision = build_snapshot_revision(
        stream_id="portable-assurance",
        sequence=0,
        snapshot_digest="1" * 64,
    )
    anchor = build_snapshot_anchor(anchor_id="portable-root-v1", genesis_revision=revision)
    return build_snapshot_checkpoint(anchor=anchor, revision=revision)


def _policy():
    return build_witness_quorum_policy(
        policy_id="portable-two-of-three",
        minimum_distinct_witnesses=2,
        allowed_witness_ids=["witness-a", "witness-b", "witness-c"],
        allowed_algorithms=["HMAC-SHA256-TEST"],
    )


def _signer(witness_id: str):
    def sign(message: bytes) -> bytes:
        return hmac.new(SECRETS[witness_id], message, hashlib.sha256).digest()

    return sign


def _verify(message: bytes, signature: bytes, algorithm: str, key_id: str, witness_id: str) -> bool:
    if algorithm != "HMAC-SHA256-TEST" or key_id != f"{witness_id}-key-v1":
        return False
    secret = SECRETS.get(witness_id)
    if secret is None:
        return False
    return hmac.compare_digest(hmac.new(secret, message, hashlib.sha256).digest(), signature)


def _receipt(witness_id: str, checkpoint):
    return create_witness_receipt(
        checkpoint=checkpoint,
        witness_id=witness_id,
        key_id=f"{witness_id}-key-v1",
        algorithm="HMAC-SHA256-TEST",
        observed_utc="2026-09-14T02:05:00Z",
        signer=_signer(witness_id),
    )


def _certificate(order=("witness-a", "witness-b")):
    checkpoint = _checkpoint()
    return build_checkpoint_quorum_certificate(
        checkpoint=checkpoint,
        policy=_policy(),
        receipts=[_receipt(witness, checkpoint) for witness in order],
        verifier=_verify,
    )


def test_certificate_is_deterministic_across_receipt_order():
    first = _certificate(("witness-a", "witness-b"))
    second = _certificate(("witness-b", "witness-a"))

    assert first.certificate_digest == second.certificate_digest
    assert verify_checkpoint_quorum_certificate(first, verifier=_verify)
    assert [receipt.witness_id for receipt in first.receipts] == ["witness-a", "witness-b"]


def test_export_import_round_trip_is_canonical_and_verifiable():
    certificate = _certificate()
    exported = export_checkpoint_quorum_certificate(certificate)
    imported = import_checkpoint_quorum_certificate(exported, verifier=_verify)

    assert imported == certificate
    assert export_checkpoint_quorum_certificate(imported) == exported


def test_certificate_rejects_checkpoint_policy_and_receipt_tampering():
    certificate = _certificate()

    bad_checkpoint = certificate.model_copy(
        update={
            "checkpoint": certificate.checkpoint.model_copy(
                update={"checkpoint_digest": "0" * 64}
            )
        }
    )
    bad_policy = certificate.model_copy(
        update={
            "policy": certificate.policy.model_copy(
                update={"policy_digest": "1" * 64}
            )
        }
    )
    bad_receipt = certificate.receipts[0].model_copy(update={"receipt_digest": "2" * 64})
    bad_receipts = certificate.model_copy(update={"receipts": (bad_receipt,) + certificate.receipts[1:]})

    assert not verify_checkpoint_quorum_certificate(bad_checkpoint, verifier=_verify)
    assert not verify_checkpoint_quorum_certificate(bad_policy, verifier=_verify)
    assert not verify_checkpoint_quorum_certificate(bad_receipts, verifier=_verify)


def test_certificate_digest_tamper_and_receipt_reordering_fail_closed():
    certificate = _certificate()
    bad_digest = certificate.model_copy(update={"certificate_digest": "f" * 64})
    reordered = certificate.model_copy(update={"receipts": tuple(reversed(certificate.receipts))})

    assert not verify_checkpoint_quorum_certificate(bad_digest, verifier=_verify)
    assert not verify_checkpoint_quorum_certificate(reordered, verifier=_verify)


def test_builder_rejects_insufficient_quorum():
    checkpoint = _checkpoint()
    with pytest.raises(ValueError):
        build_checkpoint_quorum_certificate(
            checkpoint=checkpoint,
            policy=_policy(),
            receipts=[_receipt("witness-a", checkpoint)],
            verifier=_verify,
        )


def test_import_rejects_modified_portable_json():
    certificate = _certificate()
    exported = export_checkpoint_quorum_certificate(certificate)
    modified = exported.replace(certificate.policy.policy_id, "tampered-policy", 1)

    with pytest.raises(ValueError):
        import_checkpoint_quorum_certificate(modified, verifier=_verify)
