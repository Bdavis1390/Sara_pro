from __future__ import annotations

from datetime import datetime, timezone

from .snapshot_lineage import (
    SnapshotAnchor,
    SnapshotCheckpoint,
    SnapshotRevision,
    build_snapshot_anchor,
    build_snapshot_checkpoint,
    build_snapshot_revision,
    verify_snapshot_chain,
    verify_snapshot_revision,
)
from .trust_registry import TrustKeyRecord, TrustRegistry, verify_trust_registry


TRUST_REGISTRY_STREAM_ID = "trust-registry"


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def _identity(entry: TrustKeyRecord) -> tuple[str, str, str]:
    return (entry.signer_id, entry.key_id, entry.algorithm)


def _entry_map(registry: TrustRegistry) -> dict[tuple[str, str, str], TrustKeyRecord]:
    return {_identity(entry): entry for entry in registry.entries}


def _transition_allowed(previous: TrustKeyRecord, current: TrustKeyRecord) -> bool:
    if previous.valid_from_utc != current.valid_from_utc:
        return False

    if previous.status == "ACTIVE":
        if current.status == "ACTIVE":
            return previous == current
        if current.status == "RETIRED":
            return current.valid_until_utc is not None and current.revoked_utc is None
        if current.status == "REVOKED":
            return current.revoked_utc is not None
        return False

    if previous.status == "RETIRED":
        if current.status == "RETIRED":
            return previous == current
        if current.status == "REVOKED":
            return (
                current.valid_until_utc == previous.valid_until_utc
                and current.successor_key_id == previous.successor_key_id
                and current.revoked_utc is not None
            )
        return False

    if previous.status == "REVOKED":
        return current.status == "REVOKED" and previous == current

    return False


def verify_registry_transition(previous: TrustRegistry, current: TrustRegistry) -> bool:
    if not verify_trust_registry(previous) or not verify_trust_registry(current):
        return False
    if current.registry_id != previous.registry_id:
        return False

    try:
        if _parse_utc(current.generated_utc) <= _parse_utc(previous.generated_utc):
            return False
    except (TypeError, ValueError):
        return False

    previous_entries = _entry_map(previous)
    current_entries = _entry_map(current)

    # Historical identities must remain present so retirement/revocation history
    # cannot be erased by publishing a later snapshot.
    if not set(previous_entries).issubset(current_entries):
        return False

    for identity, previous_entry in previous_entries.items():
        if not _transition_allowed(previous_entry, current_entries[identity]):
            return False

    return True


def build_registry_revision(
    registry: TrustRegistry,
    *,
    sequence: int,
    previous_revision: SnapshotRevision | None = None,
    stream_id: str = TRUST_REGISTRY_STREAM_ID,
) -> SnapshotRevision:
    if not verify_trust_registry(registry):
        raise ValueError("registry must pass digest and lifecycle validation")

    predecessor = previous_revision.revision_digest if previous_revision is not None else None
    if previous_revision is not None:
        if not verify_snapshot_revision(previous_revision):
            raise ValueError("previous revision must pass digest validation")
        if previous_revision.stream_id != stream_id:
            raise ValueError("previous revision belongs to a different stream")
        if sequence != previous_revision.sequence + 1:
            raise ValueError("sequence must advance exactly one revision")

    return build_snapshot_revision(
        stream_id=stream_id,
        sequence=sequence,
        snapshot_digest=registry.registry_digest,
        previous_revision_digest=predecessor,
    )


def build_registry_anchor(
    registry: TrustRegistry,
    *,
    anchor_id: str = "trust-registry-root-v1",
    stream_id: str = TRUST_REGISTRY_STREAM_ID,
) -> tuple[SnapshotRevision, SnapshotAnchor]:
    revision = build_registry_revision(registry, sequence=0, stream_id=stream_id)
    return revision, build_snapshot_anchor(anchor_id=anchor_id, genesis_revision=revision)


def build_registry_checkpoint(
    *,
    anchor: SnapshotAnchor,
    revision: SnapshotRevision,
) -> SnapshotCheckpoint:
    return build_snapshot_checkpoint(anchor=anchor, revision=revision)


def verify_registry_lineage(
    registries: list[TrustRegistry],
    revisions: list[SnapshotRevision],
    *,
    anchor: SnapshotAnchor,
    required_checkpoint: SnapshotCheckpoint | None = None,
) -> bool:
    if not registries or len(registries) != len(revisions):
        return False

    expected_registry_id = registries[0].registry_id
    for index, (registry, revision) in enumerate(zip(registries, revisions, strict=True)):
        if not verify_trust_registry(registry):
            return False
        if registry.registry_id != expected_registry_id:
            return False
        if revision.snapshot_digest != registry.registry_digest:
            return False
        if revision.sequence != index:
            return False
        if index > 0 and not verify_registry_transition(registries[index - 1], registry):
            return False

    return verify_snapshot_chain(
        revisions,
        anchor=anchor,
        required_checkpoint=required_checkpoint,
    )
