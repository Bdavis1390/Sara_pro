from __future__ import annotations

from .checkpoint_quorum_certificate import (
    CheckpointQuorumCertificate,
    verify_checkpoint_quorum_certificate,
)
from .checkpoint_witness import WitnessQuorumPolicy, verify_witness_quorum_policy
from .snapshot_lineage import (
    SnapshotAnchor,
    SnapshotCheckpoint,
    SnapshotRevision,
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
    verify_snapshot_chain,
)


_POLICY_STREAM_PREFIX = "quorum-policy:"


def _stream_id(authority_id: str) -> str:
    if not authority_id or len(authority_id) > 96:
        raise ValueError("authority_id must be non-empty and at most 96 characters")
    return f"{_POLICY_STREAM_PREFIX}{authority_id}"


def build_quorum_policy_revision(
    *,
    authority_id: str,
    sequence: int,
    policy: WitnessQuorumPolicy,
    previous_revision: SnapshotRevision | None = None,
) -> SnapshotRevision:
    if not verify_witness_quorum_policy(policy):
        raise ValueError("policy revision requires a valid quorum policy")

    stream_id = _stream_id(authority_id)
    if sequence == 0:
        if previous_revision is not None:
            raise ValueError("genesis policy revision cannot have a predecessor")
        previous_digest = None
    else:
        if previous_revision is None:
            raise ValueError("non-genesis policy revision requires predecessor")
        if previous_revision.stream_id != stream_id:
            raise ValueError("policy predecessor belongs to another authority stream")
        if previous_revision.sequence != sequence - 1:
            raise ValueError("policy predecessor sequence must be contiguous")
        previous_digest = previous_revision.revision_digest

    return build_snapshot_revision(
        stream_id=stream_id,
        sequence=sequence,
        snapshot_digest=policy.policy_digest,
        previous_revision_digest=previous_digest,
    )


def build_quorum_policy_anchor(*, authority_id: str, genesis_revision: SnapshotRevision) -> SnapshotAnchor:
    expected_stream = _stream_id(authority_id)
    if genesis_revision.stream_id != expected_stream:
        raise ValueError("genesis revision does not match policy authority")
    return build_snapshot_anchor(
        anchor_id=f"policy-root:{authority_id}",
        genesis_revision=genesis_revision,
    )


def build_quorum_policy_checkpoint(
    *,
    anchor: SnapshotAnchor,
    revision: SnapshotRevision,
) -> SnapshotCheckpoint:
    if not anchor.stream_id.startswith(_POLICY_STREAM_PREFIX):
        raise ValueError("anchor is not a quorum-policy lineage")
    return build_snapshot_checkpoint(anchor=anchor, revision=revision)


def verify_certificate_against_quorum_policy_history(
    certificate: CheckpointQuorumCertificate,
    *,
    revisions: list[SnapshotRevision],
    anchor: SnapshotAnchor,
    required_checkpoint: SnapshotCheckpoint,
    verifier,
) -> bool:
    if not anchor.stream_id.startswith(_POLICY_STREAM_PREFIX):
        return False
    if not verify_snapshot_chain(
        revisions,
        anchor=anchor,
        required_checkpoint=required_checkpoint,
    ):
        return False
    if not revisions:
        return False

    current_revision = revisions[-1]
    if current_revision.snapshot_digest != certificate.policy.policy_digest:
        return False

    return verify_checkpoint_quorum_certificate(certificate, verifier=verifier)
