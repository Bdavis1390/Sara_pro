from __future__ import annotations

import hashlib
import hmac

from worldshepherd_sara.checkpoint_witness import (
    build_witness_quorum_policy,
    create_witness_receipt,
    verify_checkpoint_quorum,
    verify_witness_quorum_policy,
    verify_witness_receipt,
)
from worldshepherd_sara.snapshot_lineage import (
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
)


SECRETS = {
    "witness-a": b"test-only-a",
    "witness-b": b"test-only-b",
    "witness-c": b"test-only-c",
}


def _checkpoint():
    revision = build_snapshot_revision(
        stream_id="assurance-history",
        sequence=0,
        snapshot_digest="1" * 64,
    )
    anchor = build_snapshot_anchor(anchor_id="root-v1", genesis_revision=revision)
    return build_snapshot_checkpoint(anchor=anchor, revision=revision)


def _signer(witness_id: str):
    def sign(message: bytes) -> bytes:
        return hmac.new(SECRETS[witness_id], message, hashlib.sha256).digest()

    return sign


def _verify(message: bytes, signature: bytes, algorithm: str, key_id: str, witness_id: str) -> bool:
    if algorithm != "HMAC-SHA256-TEST":
        return False
    if key_id != f"{witness_id}-key-v1":
        return False
    secret = SECRETS.get(witness_id)
    if secret is None:
        return False
    expected = hmac.new(secret, message, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def _policy():
    return build_witness_quorum_policy(
        policy_id="two-of-three",
        minimum_distinct_witnesses=2,
        allowed_witness_ids=["witness-c", "witness-a", "witness-b"],
        allowed_algorithms=["HMAC-SHA256-TEST"],
    )


def _receipt(witness_id: str, checkpoint=None):
    checkpoint = checkpoint or _checkpoint()
    return create_witness_receipt(
        checkpoint=checkpoint,
        witness_id=witness_id,
        key_id=f"{witness_id}-key-v1",
        algorithm="HMAC-SHA256-TEST",
        observed_utc="2026-09-14T01:45:00Z",
        signer=_signer(witness_id),
    )


def test_policy_is_deterministic_and_two_of_three_quorum_passes():
    checkpoint = _checkpoint()
    first = _policy()
    second = build_witness_quorum_policy(
        policy_id="two-of-three",
        minimum_distinct_witnesses=2,
        allowed_witness_ids=["witness-b", "witness-c", "witness-a"],
        allowed_algorithms=["HMAC-SHA256-TEST"],
    )

    assert first.policy_digest == second.policy_digest
    assert verify_witness_quorum_policy(first)
    assert verify_checkpoint_quorum(
        checkpoint,
        receipts=[_receipt("witness-a", checkpoint), _receipt("witness-b", checkpoint)],
        policy=first,
        verifier=_verify,
    )


def test_insufficient_quorum_fails_closed():
    checkpoint = _checkpoint()
    assert not verify_checkpoint_quorum(
        checkpoint,
        receipts=[_receipt("witness-a", checkpoint)],
        policy=_policy(),
        verifier=_verify,
    )


def test_duplicate_witness_does_not_count_twice():
    checkpoint = _checkpoint()
    receipt = _receipt("witness-a", checkpoint)
    assert not verify_checkpoint_quorum(
        checkpoint,
        receipts=[receipt, receipt],
        policy=_policy(),
        verifier=_verify,
    )


def test_receipt_for_different_checkpoint_is_rejected():
    checkpoint = _checkpoint()
    other_revision = build_snapshot_revision(
        stream_id="assurance-history",
        sequence=1,
        snapshot_digest="2" * 64,
        previous_revision_digest=(
            build_snapshot_revision(
                stream_id="assurance-history",
                sequence=0,
                snapshot_digest="1" * 64,
            ).revision_digest
        ),
    )
    genesis = build_snapshot_revision(
        stream_id="assurance-history",
        sequence=0,
        snapshot_digest="1" * 64,
    )
    anchor = build_snapshot_anchor(anchor_id="root-v1", genesis_revision=genesis)
    other_checkpoint = build_snapshot_checkpoint(anchor=anchor, revision=other_revision)
    receipt = _receipt("witness-a", other_checkpoint)

    assert not verify_witness_receipt(receipt, checkpoint=checkpoint, policy=_policy(), verifier=_verify)


def test_untrusted_witness_and_tampered_receipt_fail():
    checkpoint = _checkpoint()
    trusted = _receipt("witness-a", checkpoint)
    bad_digest = trusted.model_copy(update={"receipt_digest": "0" * 64})

    assert not verify_witness_receipt(bad_digest, checkpoint=checkpoint, policy=_policy(), verifier=_verify)

    restricted = build_witness_quorum_policy(
        policy_id="restricted",
        minimum_distinct_witnesses=1,
        allowed_witness_ids=["witness-b"],
        allowed_algorithms=["HMAC-SHA256-TEST"],
    )
    assert not verify_witness_receipt(trusted, checkpoint=checkpoint, policy=restricted, verifier=_verify)


def test_policy_tamper_and_impossible_quorum_are_rejected():
    policy = _policy()
    tampered = policy.model_copy(update={"policy_digest": "f" * 64})
    assert not verify_witness_quorum_policy(tampered)

    try:
        build_witness_quorum_policy(
            policy_id="impossible",
            minimum_distinct_witnesses=3,
            allowed_witness_ids=["witness-a", "witness-b"],
            allowed_algorithms=["HMAC-SHA256-TEST"],
        )
    except ValueError:
        pass
    else:
        raise AssertionError("impossible quorum must be rejected")
