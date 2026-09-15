from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SNAPSHOT_REVISION_SCHEMA = "WS-SNAPSHOT-REVISION-V1"
SNAPSHOT_ANCHOR_SCHEMA = "WS-SNAPSHOT-ANCHOR-V1"
SNAPSHOT_CHECKPOINT_SCHEMA = "WS-SNAPSHOT-CHECKPOINT-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class SnapshotRevision(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[SNAPSHOT_REVISION_SCHEMA] = SNAPSHOT_REVISION_SCHEMA
    stream_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    sequence: int = Field(ge=0)
    snapshot_digest: str = Field(pattern=_SHA256_PATTERN)
    previous_revision_digest: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    revision_digest: str = Field(pattern=_SHA256_PATTERN)


class SnapshotAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[SNAPSHOT_ANCHOR_SCHEMA] = SNAPSHOT_ANCHOR_SCHEMA
    anchor_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    stream_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    genesis_snapshot_digest: str = Field(pattern=_SHA256_PATTERN)
    genesis_revision_digest: str = Field(pattern=_SHA256_PATTERN)
    anchor_digest: str = Field(pattern=_SHA256_PATTERN)


class SnapshotCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[SNAPSHOT_CHECKPOINT_SCHEMA] = SNAPSHOT_CHECKPOINT_SCHEMA
    stream_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    anchor_digest: str = Field(pattern=_SHA256_PATTERN)
    sequence: int = Field(ge=0)
    revision_digest: str = Field(pattern=_SHA256_PATTERN)
    checkpoint_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _without_digest(model: BaseModel, field: str) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    payload.pop(field, None)
    return payload


def build_snapshot_revision(
    *,
    stream_id: str,
    sequence: int,
    snapshot_digest: str,
    previous_revision_digest: str | None = None,
) -> SnapshotRevision:
    if sequence == 0 and previous_revision_digest is not None:
        raise ValueError("genesis revision cannot have a predecessor")
    if sequence > 0 and previous_revision_digest is None:
        raise ValueError("non-genesis revision requires predecessor digest")

    payload: dict[str, Any] = {
        "schema": SNAPSHOT_REVISION_SCHEMA,
        "stream_id": stream_id,
        "sequence": sequence,
        "snapshot_digest": snapshot_digest,
        "previous_revision_digest": previous_revision_digest,
    }
    payload["revision_digest"] = _digest(payload)
    return SnapshotRevision.model_validate(payload)


def verify_snapshot_revision(revision: SnapshotRevision) -> bool:
    if revision.sequence == 0 and revision.previous_revision_digest is not None:
        return False
    if revision.sequence > 0 and revision.previous_revision_digest is None:
        return False
    return _digest(_without_digest(revision, "revision_digest")) == revision.revision_digest


def build_snapshot_anchor(*, anchor_id: str, genesis_revision: SnapshotRevision) -> SnapshotAnchor:
    if not verify_snapshot_revision(genesis_revision) or genesis_revision.sequence != 0:
        raise ValueError("anchor requires a valid genesis revision")

    payload: dict[str, Any] = {
        "schema": SNAPSHOT_ANCHOR_SCHEMA,
        "anchor_id": anchor_id,
        "stream_id": genesis_revision.stream_id,
        "genesis_snapshot_digest": genesis_revision.snapshot_digest,
        "genesis_revision_digest": genesis_revision.revision_digest,
    }
    payload["anchor_digest"] = _digest(payload)
    return SnapshotAnchor.model_validate(payload)


def verify_snapshot_anchor(anchor: SnapshotAnchor, genesis_revision: SnapshotRevision) -> bool:
    if _digest(_without_digest(anchor, "anchor_digest")) != anchor.anchor_digest:
        return False
    return (
        verify_snapshot_revision(genesis_revision)
        and genesis_revision.sequence == 0
        and anchor.stream_id == genesis_revision.stream_id
        and anchor.genesis_snapshot_digest == genesis_revision.snapshot_digest
        and anchor.genesis_revision_digest == genesis_revision.revision_digest
    )


def build_snapshot_checkpoint(
    *,
    anchor: SnapshotAnchor,
    revision: SnapshotRevision,
) -> SnapshotCheckpoint:
    if not verify_snapshot_revision(revision):
        raise ValueError("checkpoint requires a valid revision")
    if revision.stream_id != anchor.stream_id:
        raise ValueError("checkpoint stream must match anchor")

    payload: dict[str, Any] = {
        "schema": SNAPSHOT_CHECKPOINT_SCHEMA,
        "stream_id": revision.stream_id,
        "anchor_digest": anchor.anchor_digest,
        "sequence": revision.sequence,
        "revision_digest": revision.revision_digest,
    }
    payload["checkpoint_digest"] = _digest(payload)
    return SnapshotCheckpoint.model_validate(payload)


def verify_snapshot_checkpoint(
    checkpoint: SnapshotCheckpoint,
    *,
    anchor: SnapshotAnchor,
    revision: SnapshotRevision,
) -> bool:
    if _digest(_without_digest(checkpoint, "checkpoint_digest")) != checkpoint.checkpoint_digest:
        return False
    return (
        verify_snapshot_revision(revision)
        and checkpoint.stream_id == anchor.stream_id == revision.stream_id
        and checkpoint.anchor_digest == anchor.anchor_digest
        and checkpoint.sequence == revision.sequence
        and checkpoint.revision_digest == revision.revision_digest
    )


def verify_snapshot_chain(
    revisions: list[SnapshotRevision],
    *,
    anchor: SnapshotAnchor,
    required_checkpoint: SnapshotCheckpoint | None = None,
) -> bool:
    if not revisions or not verify_snapshot_anchor(anchor, revisions[0]):
        return False

    for index, revision in enumerate(revisions):
        if not verify_snapshot_revision(revision):
            return False
        if revision.stream_id != anchor.stream_id or revision.sequence != index:
            return False
        if index == 0:
            continue
        previous = revisions[index - 1]
        if revision.previous_revision_digest != previous.revision_digest:
            return False

    if required_checkpoint is not None:
        return verify_snapshot_checkpoint(required_checkpoint, anchor=anchor, revision=revisions[-1])
    return True
