from __future__ import annotations

import pytest

from worldshepherd_sara.snapshot_lineage import (
    SnapshotCheckpoint,
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
    verify_snapshot_anchor,
    verify_snapshot_chain,
    verify_snapshot_checkpoint,
    verify_snapshot_revision,
)


D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64


def _chain():
    r0 = build_snapshot_revision(stream_id="trust-registry", sequence=0, snapshot_digest=D0)
    r1 = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=1,
        snapshot_digest=D1,
        previous_revision_digest=r0.revision_digest,
    )
    r2 = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=2,
        snapshot_digest=D2,
        previous_revision_digest=r1.revision_digest,
    )
    anchor = build_snapshot_anchor(anchor_id="trust-root-v1", genesis_revision=r0)
    return r0, r1, r2, anchor


def test_revision_anchor_and_checkpoint_are_deterministic():
    r0, r1, r2, anchor = _chain()
    duplicate = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=2,
        snapshot_digest=D2,
        previous_revision_digest=r1.revision_digest,
    )
    checkpoint = build_snapshot_checkpoint(anchor=anchor, revision=r2)

    assert duplicate.revision_digest == r2.revision_digest
    assert verify_snapshot_revision(r0)
    assert verify_snapshot_anchor(anchor, r0)
    assert verify_snapshot_checkpoint(checkpoint, anchor=anchor, revision=r2)
    assert verify_snapshot_chain([r0, r1, r2], anchor=anchor, required_checkpoint=checkpoint)


def test_chain_rejects_gap_wrong_predecessor_and_stream_switch():
    r0, r1, r2, anchor = _chain()
    gap = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=3,
        snapshot_digest="3" * 64,
        previous_revision_digest=r2.revision_digest,
    )
    wrong_parent = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=2,
        snapshot_digest=D2,
        previous_revision_digest=r0.revision_digest,
    )
    other_stream = build_snapshot_revision(
        stream_id="other-stream",
        sequence=1,
        snapshot_digest=D1,
        previous_revision_digest=r0.revision_digest,
    )

    assert not verify_snapshot_chain([r0, r1, gap], anchor=anchor)
    assert not verify_snapshot_chain([r0, r1, wrong_parent], anchor=anchor)
    assert not verify_snapshot_chain([r0, other_stream], anchor=anchor)


def test_pinned_checkpoint_detects_rollback_and_fork():
    r0, r1, r2, anchor = _chain()
    checkpoint = build_snapshot_checkpoint(anchor=anchor, revision=r2)
    fork = build_snapshot_revision(
        stream_id="trust-registry",
        sequence=2,
        snapshot_digest="f" * 64,
        previous_revision_digest=r1.revision_digest,
    )

    assert not verify_snapshot_chain([r0, r1], anchor=anchor, required_checkpoint=checkpoint)
    assert not verify_snapshot_chain([r0, r1, fork], anchor=anchor, required_checkpoint=checkpoint)


def test_tampered_revision_anchor_or_checkpoint_fails_closed():
    r0, r1, r2, anchor = _chain()
    checkpoint = build_snapshot_checkpoint(anchor=anchor, revision=r2)

    bad_revision = r2.model_copy(update={"revision_digest": "a" * 64})
    bad_anchor = anchor.model_copy(update={"anchor_digest": "b" * 64})
    bad_checkpoint = checkpoint.model_copy(update={"checkpoint_digest": "c" * 64})

    assert not verify_snapshot_revision(bad_revision)
    assert not verify_snapshot_anchor(bad_anchor, r0)
    assert not verify_snapshot_checkpoint(bad_checkpoint, anchor=anchor, revision=r2)


def test_revision_construction_rejects_invalid_genesis_and_missing_parent():
    with pytest.raises(ValueError):
        build_snapshot_revision(
            stream_id="trust-registry",
            sequence=0,
            snapshot_digest=D0,
            previous_revision_digest="d" * 64,
        )

    with pytest.raises(ValueError):
        build_snapshot_revision(stream_id="trust-registry", sequence=1, snapshot_digest=D1)


def test_checkpoint_tamper_can_change_fields_only_if_digest_is_recomputed():
    _, _, r2, anchor = _chain()
    checkpoint = build_snapshot_checkpoint(anchor=anchor, revision=r2)
    altered = SnapshotCheckpoint.model_validate(
        {
            **checkpoint.model_dump(mode="json"),
            "sequence": 1,
        }
    )
    assert not verify_snapshot_checkpoint(altered, anchor=anchor, revision=r2)
