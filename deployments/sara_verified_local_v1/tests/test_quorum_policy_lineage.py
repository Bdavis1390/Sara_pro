from __future__ import annotations

import hashlib
import hmac

from worldshepherd_sara.checkpoint_quorum_certificate import build_checkpoint_quorum_certificate
from worldshepherd_sara.checkpoint_witness import (
    build_witness_quorum_policy,
    create_witness_receipt,
)
from worldshepherd_sara.quorum_policy_lineage import (
    build_quorum_policy_anchor,
    build_quorum_policy_checkpoint,
    build_quorum_policy_revision,
    verify_certificate_against_quorum_policy_history,
)
from worldshepherd_sara.snapshot_lineage import (
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
)


SECRETS = {
    "witness-a": b"policy-lineage-a",
    "witness-b": b"policy-lineage-b",
    "witness-c": b"policy-lineage-c",
}


def _verify(message: bytes, signature: bytes, algorithm: str, key_id: str, witness_id: str) -> bool:
    if algorithm != "HMAC-SHA256-TEST" or key_id != f"{witness_id}-key-v1":
        return False
    secret = SECRETS.get(witness_id)
    if secret is None:
        return False
    return hmac.compare_digest(hmac.new(secret, message, hashlib.sha256).digest(), signature)


def _signer(witness_id: str):
    def sign(message: bytes) -> bytes:
        return hmac.new(SECRETS[witness_id], message, hashlib.sha256).digest()

    return sign


def _evidence_checkpoint():
    revision = build_snapshot_revision(
        stream_id="evidence-history",
        sequence=0,
        snapshot_digest="a" * 64,
    )
    anchor = build_snapshot_anchor(anchor_id="evidence-root", genesis_revision=revision)
    return build_snapshot_checkpoint(anchor=anchor, revision=revision)


def _policy(policy_id: str, witnesses=("witness-a", "witness-b", "witness-c"), minimum=2):
    return build_witness_quorum_policy(
        policy_id=policy_id,
        minimum_distinct_witnesses=minimum,
        allowed_witness_ids=list(witnesses),
        allowed_algorithms=["HMAC-SHA256-TEST"],
    )


def _certificate(policy, witnesses=("witness-a", "witness-b")):
    checkpoint = _evidence_checkpoint()
    receipts = [
        create_witness_receipt(
            checkpoint=checkpoint,
            witness_id=witness_id,
            key_id=f"{witness_id}-key-v1",
            algorithm="HMAC-SHA256-TEST",
            observed_utc="2026-09-14T02:20:00Z",
            signer=_signer(witness_id),
        )
        for witness_id in witnesses
    ]
    return build_checkpoint_quorum_certificate(
        checkpoint=checkpoint,
        policy=policy,
        receipts=receipts,
        verifier=_verify,
    )


def test_certificate_must_match_current_authoritative_policy():
    authority = "assurance-board"
    p0 = _policy("policy-v1")
    p1 = _policy("policy-v2")
    r0 = build_quorum_policy_revision(authority_id=authority, sequence=0, policy=p0)
    r1 = build_quorum_policy_revision(
        authority_id=authority,
        sequence=1,
        policy=p1,
        previous_revision=r0,
    )
    anchor = build_quorum_policy_anchor(authority_id=authority, genesis_revision=r0)
    checkpoint = build_quorum_policy_checkpoint(anchor=anchor, revision=r1)

    current_certificate = _certificate(p1)
    old_certificate = _certificate(p0)

    assert verify_certificate_against_quorum_policy_history(
        current_certificate,
        revisions=[r0, r1],
        anchor=anchor,
        required_checkpoint=checkpoint,
        verifier=_verify,
    )
    assert not verify_certificate_against_quorum_policy_history(
        old_certificate,
        revisions=[r0, r1],
        anchor=anchor,
        required_checkpoint=checkpoint,
        verifier=_verify,
    )


def test_self_selected_valid_policy_is_rejected_when_not_authoritative():
    authority = "assurance-board"
    authoritative = _policy("approved")
    attacker_selected = _policy("self-selected")
    revision = build_quorum_policy_revision(
        authority_id=authority,
        sequence=0,
        policy=authoritative,
    )
    anchor = build_quorum_policy_anchor(authority_id=authority, genesis_revision=revision)
    checkpoint = build_quorum_policy_checkpoint(anchor=anchor, revision=revision)
    certificate = _certificate(attacker_selected)

    assert not verify_certificate_against_quorum_policy_history(
        certificate,
        revisions=[revision],
        anchor=anchor,
        required_checkpoint=checkpoint,
        verifier=_verify,
    )


def test_forked_policy_history_fails_pinned_checkpoint():
    authority = "assurance-board"
    p0 = _policy("policy-v1")
    p1 = _policy("policy-v2")
    fork_policy = _policy("policy-fork")
    r0 = build_quorum_policy_revision(authority_id=authority, sequence=0, policy=p0)
    r1 = build_quorum_policy_revision(
        authority_id=authority,
        sequence=1,
        policy=p1,
        previous_revision=r0,
    )
    fork = build_quorum_policy_revision(
        authority_id=authority,
        sequence=1,
        policy=fork_policy,
        previous_revision=r0,
    )
    anchor = build_quorum_policy_anchor(authority_id=authority, genesis_revision=r0)
    checkpoint = build_quorum_policy_checkpoint(anchor=anchor, revision=r1)
    fork_certificate = _certificate(fork_policy)

    assert not verify_certificate_against_quorum_policy_history(
        fork_certificate,
        revisions=[r0, fork],
        anchor=anchor,
        required_checkpoint=checkpoint,
        verifier=_verify,
    )


def test_policy_revision_rejects_wrong_authority_or_sequence():
    p0 = _policy("policy-v1")
    r0 = build_quorum_policy_revision(authority_id="authority-a", sequence=0, policy=p0)

    try:
        build_quorum_policy_revision(
            authority_id="authority-b",
            sequence=1,
            policy=_policy("policy-v2"),
            previous_revision=r0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("cross-authority predecessor must be rejected")

    try:
        build_quorum_policy_revision(
            authority_id="authority-a",
            sequence=2,
            policy=_policy("policy-v3"),
            previous_revision=r0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("non-contiguous policy sequence must be rejected")
