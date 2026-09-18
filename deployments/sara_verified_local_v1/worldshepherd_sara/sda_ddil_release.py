from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .mission_replay import MissionEvent
from .models import AuditRecord
from .qualification import canonical_digest
from .sda_release_authorization import SdaReleaseReceipt


SDA_DDIL_JOURNAL_SCHEMA = "WS-SDA-DDIL-RELEASE-JOURNAL-V1"
SDA_DDIL_RECORD_SCHEMA = "WS-SDA-DDIL-RELEASE-RECORD-V1"
SDA_DDIL_RECONCILE_SCHEMA = "WS-SDA-DDIL-RECONCILIATION-V1"
MAX_DDIL_RELEASE_RECORDS = 1024


class SdaDdilError(RuntimeError):
    pass


class SdaDdilConflict(SdaDdilError):
    pass


class SdaDdilJournalFull(SdaDdilError):
    pass


class SdaDdilAppendOutcome(str, Enum):
    STORED = "STORED"
    DEDUPLICATED = "DEDUPLICATED"


class SdaDdilReconciliationState(str, Enum):
    MATCHED = "MATCHED"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"
    CONFLICT = "CONFLICT"


class SdaDdilReleaseRecord(BaseModel):
    """Durable disconnected-operation record for an already-consumed G6 receipt.

    The record is evidence about one bounded analytic-release authorization. It is
    not a new authorization and cannot extend, replace, or upgrade the G6 receipt.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_DDIL_RECORD_SCHEMA] = SDA_DDIL_RECORD_SCHEMA
    origin_node: str = Field(min_length=1, max_length=128)
    logical_clock: int = Field(ge=1)
    authority: int = Field(ge=0, le=1000)
    recorded_at: datetime
    receipt: SdaReleaseReceipt
    receipt_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @classmethod
    def from_receipt(
        cls,
        receipt: SdaReleaseReceipt,
        *,
        origin_node: str,
        logical_clock: int,
        authority: int,
        recorded_at: datetime | None = None,
    ) -> "SdaDdilReleaseRecord":
        return cls(
            origin_node=origin_node,
            logical_clock=logical_clock,
            authority=authority,
            recorded_at=(recorded_at or datetime.now(timezone.utc)),
            receipt=receipt,
            receipt_digest=canonical_digest(receipt),
        )

    def semantic_digest(self) -> str:
        return canonical_digest(self)

    def stable_echo_event_id(self) -> str:
        # Authorization + origin-node identity stays stable across retransmission
        # and mutated semantic content from that node so ECHO can detect mutation
        # without treating a second honest replica node as the same event.
        stable_identity = (
            self.receipt.authorization_id + "\x00" + self.origin_node
        ).encode("utf-8")
        suffix = hashlib.sha256(stable_identity).hexdigest()
        return f"SARA-EVENT-SDA-DDIL-RELEASE-{suffix}"


class SdaDdilReconciliationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_id: str
    state: SdaDdilReconciliationState
    left_receipt_digest: str | None = None
    right_receipt_digest: str | None = None
    selected_receipt_digest: str | None = None
    reason: str


class SdaDdilReconciliationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_DDIL_RECONCILE_SCHEMA] = SDA_DDIL_RECONCILE_SCHEMA
    entries: list[SdaDdilReconciliationEntry]
    merged_records: list[SdaDdilReleaseRecord]
    conflicts: list[SdaDdilReconciliationEntry]
    claims_boundary: str = (
        "Deterministic software reconciliation of disconnected analytic-release "
        "receipt journals only. Conflicting semantics for one authorization ID are "
        "never auto-selected. This is not distributed consensus, operational link "
        "assurance, recipient acknowledgement, or authority to re-release evidence."
    )


def reconcile_release_records(
    left: Iterable[SdaDdilReleaseRecord],
    right: Iterable[SdaDdilReleaseRecord],
) -> SdaDdilReconciliationPlan:
    left_map = _unique_by_authorization(left, side="left")
    right_map = _unique_by_authorization(right, side="right")

    entries: list[SdaDdilReconciliationEntry] = []
    merged: list[SdaDdilReleaseRecord] = []
    conflicts: list[SdaDdilReconciliationEntry] = []

    for authorization_id in sorted(set(left_map) | set(right_map)):
        l = left_map.get(authorization_id)
        r = right_map.get(authorization_id)

        if l is None:
            assert r is not None
            entry = SdaDdilReconciliationEntry(
                authorization_id=authorization_id,
                state=SdaDdilReconciliationState.RIGHT_ONLY,
                right_receipt_digest=r.receipt_digest,
                selected_receipt_digest=r.receipt_digest,
                reason="authorization receipt exists only on right journal",
            )
            merged.append(r)
        elif r is None:
            entry = SdaDdilReconciliationEntry(
                authorization_id=authorization_id,
                state=SdaDdilReconciliationState.LEFT_ONLY,
                left_receipt_digest=l.receipt_digest,
                selected_receipt_digest=l.receipt_digest,
                reason="authorization receipt exists only on left journal",
            )
            merged.append(l)
        elif l.receipt_digest == r.receipt_digest:
            # Same G6 receipt semantics. Metadata may differ because each node has
            # its own local logical clock/time. Deterministic selection is safe.
            selected = sorted(
                [l, r],
                key=lambda item: (
                    -item.logical_clock,
                    -item.authority,
                    item.origin_node,
                    item.recorded_at.isoformat(),
                ),
            )[0]
            entry = SdaDdilReconciliationEntry(
                authorization_id=authorization_id,
                state=SdaDdilReconciliationState.MATCHED,
                left_receipt_digest=l.receipt_digest,
                right_receipt_digest=r.receipt_digest,
                selected_receipt_digest=selected.receipt_digest,
                reason="both journals preserve identical G6 receipt semantics",
            )
            merged.append(selected)
        else:
            entry = SdaDdilReconciliationEntry(
                authorization_id=authorization_id,
                state=SdaDdilReconciliationState.CONFLICT,
                left_receipt_digest=l.receipt_digest,
                right_receipt_digest=r.receipt_digest,
                selected_receipt_digest=None,
                reason=(
                    "same authorization ID has different G6 receipt semantics; "
                    "automatic resolution is forbidden"
                ),
            )
            conflicts.append(entry)

        entries.append(entry)

    return SdaDdilReconciliationPlan(
        entries=entries,
        merged_records=sorted(
            merged,
            key=lambda item: (
                item.receipt.consumed_at.astimezone(timezone.utc),
                item.receipt.authorization_id,
                item.origin_node,
            ),
        ),
        conflicts=conflicts,
    )


def _unique_by_authorization(
    records: Iterable[SdaDdilReleaseRecord],
    *,
    side: str,
) -> dict[str, SdaDdilReleaseRecord]:
    result: dict[str, SdaDdilReleaseRecord] = {}
    for record in records:
        authorization_id = record.receipt.authorization_id
        prior = result.get(authorization_id)
        if prior is not None and prior.receipt_digest != record.receipt_digest:
            raise SdaDdilConflict(
                f"{side} input contains conflicting receipt semantics for one authorization ID"
            )
        if prior is None:
            result[authorization_id] = record
    return result


def sda_ddil_release_audit_record(
    record: SdaDdilReleaseRecord,
) -> AuditRecord:
    return AuditRecord(
        timestamp=record.recorded_at.astimezone(timezone.utc).isoformat(),
        event="sda_ddil_release_receipt",
        actor=record.origin_node,
        payload={
            "_outbox_event_id": record.stable_echo_event_id(),
            "_delivery_semantics": "AT_LEAST_ONCE",
            "schema": SDA_DDIL_RECORD_SCHEMA,
            "authorization_id": record.receipt.authorization_id,
            "receipt_digest": record.receipt_digest,
            "record_semantic_digest": record.semantic_digest(),
            "logical_clock": record.logical_clock,
            "authority": record.authority,
            "receipt": record.receipt.model_dump(mode="json"),
            "claims_boundary": (
                "Disconnected/rejoin evidence for a previously consumed G6 analytic "
                "release authorization. This event is not a new release authorization."
            ),
        },
    )


def ddil_records_to_mission_events(
    records: Iterable[SdaDdilReleaseRecord],
    *,
    starting_sequence: int = 1,
    t0: datetime | None = None,
) -> tuple[MissionEvent, ...]:
    ordered = sorted(
        records,
        key=lambda item: (
            item.receipt.consumed_at.astimezone(timezone.utc),
            item.receipt.authorization_id,
            item.origin_node,
        ),
    )
    if starting_sequence < 1:
        raise ValueError("starting_sequence must be at least 1")
    if not ordered:
        return ()

    origin = (
        t0.astimezone(timezone.utc)
        if t0 is not None
        else ordered[0].receipt.consumed_at.astimezone(timezone.utc)
    )

    events: list[MissionEvent] = []
    for offset, record in enumerate(ordered):
        consumed = record.receipt.consumed_at.astimezone(timezone.utc)
        delta = max(0.0, (consumed - origin).total_seconds())
        events.append(
            MissionEvent(
                sequence=starting_sequence + offset,
                t_seconds=delta,
                source=record.origin_node,
                event_type="sda_analytic_release_receipt",
                payload={
                    "authorization_id": record.receipt.authorization_id,
                    "receipt_digest": record.receipt_digest,
                    "hypothesis_set_digest": record.receipt.hypothesis_set_digest,
                    "payload_digest": record.receipt.payload_digest,
                    "policy_revision_digest": record.receipt.policy_revision_digest,
                    "destination": record.receipt.destination,
                    "releasability_tags": list(record.receipt.releasability_tags),
                    "human_approval_id": record.receipt.human_approval_id,
                    "human_approver": record.receipt.human_approver,
                    "claims_boundary": (
                        "Replay evidence only; does not authorize another release or "
                        "establish recipient acceptance."
                    ),
                },
            )
        )
    return tuple(events)


class SdaDdilReleaseJournal:
    """Bounded durable SQLite journal for disconnected G6 release receipts."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise SdaDdilError("DDIL journal data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / "sda-ddil-release.db"
        self._reject_database_symlink()
        self._initialize()

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise SdaDdilError("DDIL journal data directory must be a real directory")
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()

        if status.st_uid != os.geteuid():
            raise SdaDdilError("DDIL journal data directory must be owned by service UID")
        if stat.S_IMODE(status.st_mode) != 0o700:
            self.data_dir.chmod(0o700)
            if stat.S_IMODE(self.data_dir.stat().st_mode) != 0o700:
                raise SdaDdilError("DDIL journal data directory must be mode 0700")

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise SdaDdilError("DDIL journal database must be a regular file")
            if status.st_uid != os.geteuid():
                raise SdaDdilError("DDIL journal database must be owned by service UID")

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.db_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise SdaDdilError("unable to open DDIL journal") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS release_records (
                    authorization_id TEXT PRIMARY KEY,
                    receipt_digest TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conflicts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    authorization_id TEXT NOT NULL,
                    stored_receipt_digest TEXT NOT NULL,
                    observed_receipt_digest TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (SDA_DDIL_JOURNAL_SCHEMA,),
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if row is None or row["value"] != SDA_DDIL_JOURNAL_SCHEMA:
                raise SdaDdilError("DDIL journal schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise SdaDdilError("DDIL journal integrity check failed")
        except sqlite3.Error as exc:
            raise SdaDdilError("unable to initialize DDIL journal") from exc
        finally:
            connection.close()
        self.db_path.chmod(0o600)

    def append(
        self,
        record: SdaDdilReleaseRecord,
    ) -> SdaDdilAppendOutcome:
        authorization_id = record.receipt.authorization_id
        payload = json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        now = datetime.now(timezone.utc).isoformat()

        connection = self._connect()
        conflict: tuple[str, str] | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT receipt_digest FROM release_records WHERE authorization_id=?",
                (authorization_id,),
            ).fetchone()

            if row is not None:
                stored_digest = str(row["receipt_digest"])
                if stored_digest == record.receipt_digest:
                    connection.commit()
                    return SdaDdilAppendOutcome.DEDUPLICATED
                connection.execute(
                    """
                    INSERT INTO conflicts(
                        authorization_id, stored_receipt_digest,
                        observed_receipt_digest, observed_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        authorization_id,
                        stored_digest,
                        record.receipt_digest,
                        now,
                    ),
                )
                connection.commit()
                conflict = (stored_digest, record.receipt_digest)
            else:
                count = connection.execute(
                    "SELECT COUNT(*) FROM release_records"
                ).fetchone()[0]
                if count >= MAX_DDIL_RELEASE_RECORDS:
                    raise SdaDdilJournalFull("DDIL release journal capacity reached")
                connection.execute(
                    """
                    INSERT INTO release_records(
                        authorization_id, receipt_digest, record_json
                    ) VALUES (?, ?, ?)
                    """,
                    (authorization_id, record.receipt_digest, payload),
                )
                connection.commit()
                return SdaDdilAppendOutcome.STORED
        except (sqlite3.Error, SdaDdilError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

        if conflict is not None:
            raise SdaDdilConflict(
                "same authorization ID was observed with different receipt semantics"
            )
        raise SdaDdilError("unexpected DDIL journal append state")

    def all_records(self) -> list[SdaDdilReleaseRecord]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT record_json FROM release_records ORDER BY authorization_id"
            ).fetchall()
            records = [
                SdaDdilReleaseRecord.model_validate_json(row["record_json"])
                for row in rows
            ]
            return records
        finally:
            connection.close()

    def health(self) -> dict[str, object]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            quick_ok = quick is not None and quick[0] == "ok"
            rows = connection.execute(
                "SELECT authorization_id, receipt_digest, record_json FROM release_records"
            ).fetchall()
            conflicts = connection.execute(
                "SELECT COUNT(*) FROM conflicts"
            ).fetchone()[0]
        except sqlite3.Error as exc:
            raise SdaDdilError("unable to inspect DDIL journal") from exc
        finally:
            connection.close()

        malformed = 0
        for row in rows:
            try:
                record = SdaDdilReleaseRecord.model_validate_json(row["record_json"])
                if record.receipt.authorization_id != row["authorization_id"]:
                    malformed += 1
                elif record.receipt_digest != row["receipt_digest"]:
                    malformed += 1
                elif canonical_digest(record.receipt) != record.receipt_digest:
                    malformed += 1
            except (ValueError, TypeError):
                malformed += 1

        return {
            "ok": quick_ok
            and malformed == 0
            and len(rows) <= MAX_DDIL_RELEASE_RECORDS,
            "sqlite_quick_check": "ok" if quick_ok else "failed",
            "stored_records": len(rows),
            "capacity": MAX_DDIL_RELEASE_RECORDS,
            "semantic_integrity_errors": malformed,
            "rejected_conflicts": conflicts,
        }
