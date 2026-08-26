from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .qualification import canonical_digest


@dataclass(frozen=True)
class ConfigurationSnapshot:
    snapshot_id: str
    parent_digest: str | None
    payload: dict[str, Any]
    created_utc: str
    actor: str
    reason: str
    digest: str


def create_snapshot(
    *,
    snapshot_id: str,
    payload: dict[str, Any],
    created_utc: str,
    actor: str,
    reason: str,
    parent_digest: str | None = None,
) -> ConfigurationSnapshot:
    material = {
        "snapshot_id": snapshot_id,
        "parent_digest": parent_digest,
        "payload": payload,
        "created_utc": created_utc,
        "actor": actor,
        "reason": reason,
    }
    return ConfigurationSnapshot(
        snapshot_id=snapshot_id,
        parent_digest=parent_digest,
        payload=payload,
        created_utc=created_utc,
        actor=actor,
        reason=reason,
        digest=canonical_digest(material),
    )


class ConfigurationCustodyLedger:
    """Append-only in-memory configuration lineage model.

    Persistence should be provided by SARA/ECHO storage. The ledger makes
    version lineage explicit and detects broken parent references; it is not a
    cryptographic signing service or external configuration-management authority.
    """

    def __init__(self) -> None:
        self._snapshots: list[ConfigurationSnapshot] = []
        self._by_digest: dict[str, ConfigurationSnapshot] = {}

    def append(self, snapshot: ConfigurationSnapshot) -> None:
        if snapshot.digest in self._by_digest:
            if self._by_digest[snapshot.digest] != snapshot:
                raise ValueError("digest collision or inconsistent snapshot")
            return
        if snapshot.parent_digest is not None and snapshot.parent_digest not in self._by_digest:
            raise ValueError("parent configuration digest is not present in custody ledger")
        if self._snapshots:
            expected_parent = self._snapshots[-1].digest
            if snapshot.parent_digest != expected_parent:
                raise ValueError("new configuration snapshot must chain from current head")
        elif snapshot.parent_digest is not None:
            raise ValueError("first configuration snapshot cannot have a parent")
        self._snapshots.append(snapshot)
        self._by_digest[snapshot.digest] = snapshot

    def head(self) -> ConfigurationSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def snapshot(self, digest: str) -> ConfigurationSnapshot:
        if digest not in self._by_digest:
            raise KeyError(digest)
        return self._by_digest[digest]

    def verify_chain(self) -> bool:
        previous: str | None = None
        for snapshot in self._snapshots:
            if snapshot.parent_digest != previous:
                return False
            material = {
                "snapshot_id": snapshot.snapshot_id,
                "parent_digest": snapshot.parent_digest,
                "payload": snapshot.payload,
                "created_utc": snapshot.created_utc,
                "actor": snapshot.actor,
                "reason": snapshot.reason,
            }
            if snapshot.digest != canonical_digest(material):
                return False
            previous = snapshot.digest
        return True

    def rollback_snapshot(
        self,
        *,
        target_digest: str,
        snapshot_id: str,
        created_utc: str,
        actor: str,
        reason: str,
    ) -> ConfigurationSnapshot:
        target = self.snapshot(target_digest)
        head = self.head()
        return create_snapshot(
            snapshot_id=snapshot_id,
            payload=dict(target.payload),
            created_utc=created_utc,
            actor=actor,
            reason=reason,
            parent_digest=head.digest if head else None,
        )

    def records(self) -> tuple[ConfigurationSnapshot, ...]:
        return tuple(self._snapshots)
