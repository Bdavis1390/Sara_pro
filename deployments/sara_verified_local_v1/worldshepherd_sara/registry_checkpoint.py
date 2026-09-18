from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


REGISTRY_CHECKPOINT_META_KEY = "SARA_REGISTRY_CHECKPOINT"
REGISTRY_CHECKPOINT_META_SCHEMA = "WS-SARA-REGISTRY-CHECKPOINT-META-V1"
REGISTRY_CHECKPOINT_RECORD_SCHEMA = "WS-SARA-REGISTRY-CHECKPOINT-JOURNAL-V1"
ZERO_HASH = "0" * 64
VALID_RECORD_TYPES = frozenset({"GENESIS", "PREPARE", "COMMIT", "ABORT"})


class RegistryCheckpointIntegrityError(RuntimeError):
    """Raised when registry state and checkpoint history cannot be reconciled."""


@dataclass(frozen=True)
class VerifiedCheckpointJournal:
    tail_record_hash: str
    tail_sequence: int
    last_commit: dict[str, Any]
    pending_prepare: dict[str, Any] | None


@dataclass(frozen=True)
class CheckpointRecoveryPlan:
    action: Literal["HEALTHY", "RECOVER_COMMIT", "RECOVER_ABORT"]
    journal: VerifiedCheckpointJournal
    recovery_record: dict[str, Any] | None = None


def utc_iso(value: datetime | None = None) -> str:
    current = (value or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current.isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


def registry_state_without_checkpoint(registry: dict[str, Any]) -> dict[str, Any]:
    state = dict(registry)
    state.pop(REGISTRY_CHECKPOINT_META_KEY, None)
    return state


def registry_state_root_sha256(registry: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(registry_state_without_checkpoint(registry))
    ).hexdigest()


def checkpoint_metadata(
    *,
    generation: int,
    commit_hash: str,
    state_root_sha256: str,
) -> dict[str, Any]:
    if generation < 0:
        raise ValueError("checkpoint generation must be non-negative")
    if not _is_sha256(commit_hash) or not _is_sha256(state_root_sha256):
        raise ValueError("checkpoint metadata hashes must be SHA-256 hex digests")
    return {
        "schema": REGISTRY_CHECKPOINT_META_SCHEMA,
        "generation": generation,
        "commit_hash": commit_hash,
        "state_root_sha256": state_root_sha256,
    }


def parse_checkpoint_metadata(registry: dict[str, Any]) -> dict[str, Any] | None:
    raw = registry.get(REGISTRY_CHECKPOINT_META_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise RegistryCheckpointIntegrityError("registry checkpoint metadata is malformed")
    if raw.get("schema") != REGISTRY_CHECKPOINT_META_SCHEMA:
        raise RegistryCheckpointIntegrityError("registry checkpoint metadata schema is invalid")
    generation = raw.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        raise RegistryCheckpointIntegrityError("registry checkpoint generation is invalid")
    if not _is_sha256(raw.get("commit_hash")):
        raise RegistryCheckpointIntegrityError("registry checkpoint commit hash is invalid")
    if not _is_sha256(raw.get("state_root_sha256")):
        raise RegistryCheckpointIntegrityError("registry checkpoint state root is invalid")
    return dict(raw)


def _record_hash(record_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(record_without_hash)).hexdigest()


def make_checkpoint_record(
    *,
    record_type: str,
    sequence: int,
    tx_id: str,
    generation: int,
    previous_record_hash: str,
    previous_commit_hash: str,
    old_state_root_sha256: str,
    new_state_root_sha256: str,
    event_time: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError("invalid checkpoint record type")
    if sequence < 1 or generation < 0 or not tx_id:
        raise ValueError("invalid checkpoint sequence, generation, or tx_id")
    for value in (
        previous_record_hash,
        previous_commit_hash,
        old_state_root_sha256,
        new_state_root_sha256,
    ):
        if not _is_sha256(value):
            raise ValueError("checkpoint record hash field is invalid")
    record: dict[str, Any] = {
        "schema": REGISTRY_CHECKPOINT_RECORD_SCHEMA,
        "record_type": record_type,
        "sequence": sequence,
        "tx_id": tx_id,
        "generation": generation,
        "previous_record_hash": previous_record_hash,
        "previous_commit_hash": previous_commit_hash,
        "old_state_root_sha256": old_state_root_sha256,
        "new_state_root_sha256": new_state_root_sha256,
        "event_time": event_time,
        "reason": reason,
    }
    record["record_hash"] = _record_hash(record)
    return record


def make_genesis_record(
    registry: dict[str, Any],
    *,
    event_time: str | None = None,
) -> dict[str, Any]:
    root = registry_state_root_sha256(registry)
    return make_checkpoint_record(
        record_type="GENESIS",
        sequence=1,
        tx_id="REGISTRY-GENESIS",
        generation=0,
        previous_record_hash=ZERO_HASH,
        previous_commit_hash=ZERO_HASH,
        old_state_root_sha256=ZERO_HASH,
        new_state_root_sha256=root,
        event_time=event_time or utc_iso(),
    )


def make_transaction_records(
    current_registry: dict[str, Any],
    updated_registry: dict[str, Any],
    *,
    journal: VerifiedCheckpointJournal,
    event_time: str | None = None,
    tx_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if journal.pending_prepare is not None:
        raise RegistryCheckpointIntegrityError(
            "cannot start registry transaction while checkpoint recovery is pending"
        )
    current_meta = parse_checkpoint_metadata(current_registry)
    if current_meta is None:
        raise RegistryCheckpointIntegrityError("registry checkpoint metadata is missing")
    if current_meta["commit_hash"] != journal.last_commit["record_hash"]:
        raise RegistryCheckpointIntegrityError(
            "registry checkpoint commit does not match journal before transaction"
        )

    old_root = registry_state_root_sha256(current_registry)
    new_root = registry_state_root_sha256(updated_registry)
    if old_root != current_meta["state_root_sha256"]:
        raise RegistryCheckpointIntegrityError(
            "registry state root does not match checkpoint metadata before transaction"
        )

    generation = int(current_meta["generation"]) + 1
    stable_tx_id = tx_id or f"REGISTRY-TX-{secrets.token_hex(16)}"
    stable_time = event_time or utc_iso()
    prepare = make_checkpoint_record(
        record_type="PREPARE",
        sequence=journal.tail_sequence + 1,
        tx_id=stable_tx_id,
        generation=generation,
        previous_record_hash=journal.tail_record_hash,
        previous_commit_hash=current_meta["commit_hash"],
        old_state_root_sha256=old_root,
        new_state_root_sha256=new_root,
        event_time=stable_time,
    )
    commit = make_checkpoint_record(
        record_type="COMMIT",
        sequence=prepare["sequence"] + 1,
        tx_id=stable_tx_id,
        generation=generation,
        previous_record_hash=prepare["record_hash"],
        previous_commit_hash=current_meta["commit_hash"],
        old_state_root_sha256=old_root,
        new_state_root_sha256=new_root,
        event_time=stable_time,
    )
    final_registry = dict(updated_registry)
    final_registry[REGISTRY_CHECKPOINT_META_KEY] = checkpoint_metadata(
        generation=generation,
        commit_hash=commit["record_hash"],
        state_root_sha256=new_root,
    )
    return prepare, commit, final_registry


def expected_commit_for_prepare(prepare: dict[str, Any]) -> dict[str, Any]:
    if prepare.get("record_type") != "PREPARE":
        raise ValueError("expected PREPARE checkpoint record")
    return make_checkpoint_record(
        record_type="COMMIT",
        sequence=int(prepare["sequence"]) + 1,
        tx_id=str(prepare["tx_id"]),
        generation=int(prepare["generation"]),
        previous_record_hash=str(prepare["record_hash"]),
        previous_commit_hash=str(prepare["previous_commit_hash"]),
        old_state_root_sha256=str(prepare["old_state_root_sha256"]),
        new_state_root_sha256=str(prepare["new_state_root_sha256"]),
        event_time=str(prepare["event_time"]),
    )


def make_abort_for_prepare(
    prepare: dict[str, Any],
    *,
    reason: str,
    event_time: str | None = None,
) -> dict[str, Any]:
    if prepare.get("record_type") != "PREPARE":
        raise ValueError("expected PREPARE checkpoint record")
    if not reason:
        raise ValueError("checkpoint abort reason is required")
    return make_checkpoint_record(
        record_type="ABORT",
        sequence=int(prepare["sequence"]) + 1,
        tx_id=str(prepare["tx_id"]),
        generation=int(prepare["generation"]),
        previous_record_hash=str(prepare["record_hash"]),
        previous_commit_hash=str(prepare["previous_commit_hash"]),
        old_state_root_sha256=str(prepare["old_state_root_sha256"]),
        new_state_root_sha256=str(prepare["new_state_root_sha256"]),
        event_time=event_time or utc_iso(),
        reason=reason,
    )


def _validate_record_shape(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RegistryCheckpointIntegrityError("checkpoint journal record is not an object")
    required = {
        "schema",
        "record_type",
        "sequence",
        "tx_id",
        "generation",
        "previous_record_hash",
        "previous_commit_hash",
        "old_state_root_sha256",
        "new_state_root_sha256",
        "event_time",
        "reason",
        "record_hash",
    }
    if set(record) != required:
        raise RegistryCheckpointIntegrityError("checkpoint journal record fields are invalid")
    if record.get("schema") != REGISTRY_CHECKPOINT_RECORD_SCHEMA:
        raise RegistryCheckpointIntegrityError("checkpoint journal schema is invalid")
    if record.get("record_type") not in VALID_RECORD_TYPES:
        raise RegistryCheckpointIntegrityError("checkpoint journal record type is invalid")
    if not isinstance(record.get("sequence"), int) or isinstance(record.get("sequence"), bool):
        raise RegistryCheckpointIntegrityError("checkpoint journal sequence is invalid")
    if not isinstance(record.get("generation"), int) or isinstance(record.get("generation"), bool):
        raise RegistryCheckpointIntegrityError("checkpoint journal generation is invalid")
    if record["sequence"] < 1 or record["generation"] < 0:
        raise RegistryCheckpointIntegrityError("checkpoint journal counters are invalid")
    if not isinstance(record.get("tx_id"), str) or not record["tx_id"]:
        raise RegistryCheckpointIntegrityError("checkpoint journal tx_id is invalid")
    if not isinstance(record.get("event_time"), str) or not record["event_time"]:
        raise RegistryCheckpointIntegrityError("checkpoint journal event_time is invalid")
    try:
        parsed_time = datetime.fromisoformat(record["event_time"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryCheckpointIntegrityError("checkpoint journal event_time is invalid") from exc
    if parsed_time.tzinfo is None:
        raise RegistryCheckpointIntegrityError("checkpoint journal event_time must be timezone-aware")
    for field in (
        "previous_record_hash",
        "previous_commit_hash",
        "old_state_root_sha256",
        "new_state_root_sha256",
        "record_hash",
    ):
        if not _is_sha256(record.get(field)):
            raise RegistryCheckpointIntegrityError(f"checkpoint journal {field} is invalid")
    if record["record_type"] == "ABORT":
        if not isinstance(record.get("reason"), str) or not record["reason"]:
            raise RegistryCheckpointIntegrityError("checkpoint ABORT reason is invalid")
    elif record.get("reason") is not None:
        raise RegistryCheckpointIntegrityError("checkpoint non-ABORT record must not have reason")

    unhashed = dict(record)
    actual = str(unhashed.pop("record_hash"))
    if _record_hash(unhashed) != actual:
        raise RegistryCheckpointIntegrityError("checkpoint journal record hash mismatch")
    return dict(record)


def verify_checkpoint_journal(records: list[dict[str, Any]]) -> VerifiedCheckpointJournal:
    if not records:
        raise RegistryCheckpointIntegrityError("checkpoint journal is empty")

    previous_record_hash = ZERO_HASH
    last_commit: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None

    for index, raw in enumerate(records, start=1):
        record = _validate_record_shape(raw)
        if record["sequence"] != index:
            raise RegistryCheckpointIntegrityError("checkpoint journal sequence is not contiguous")
        if record["previous_record_hash"] != previous_record_hash:
            raise RegistryCheckpointIntegrityError("checkpoint journal hash chain is broken")

        record_type = record["record_type"]
        if index == 1:
            if (
                record_type != "GENESIS"
                or record["generation"] != 0
                or record["previous_record_hash"] != ZERO_HASH
                or record["previous_commit_hash"] != ZERO_HASH
                or record["old_state_root_sha256"] != ZERO_HASH
            ):
                raise RegistryCheckpointIntegrityError("checkpoint journal genesis is invalid")
            last_commit = record
        elif record_type == "GENESIS":
            raise RegistryCheckpointIntegrityError("checkpoint journal contains duplicate genesis")
        elif record_type == "PREPARE":
            if pending is not None:
                raise RegistryCheckpointIntegrityError("checkpoint journal has nested PREPARE")
            assert last_commit is not None
            if record["generation"] != last_commit["generation"] + 1:
                raise RegistryCheckpointIntegrityError("checkpoint PREPARE generation is invalid")
            if record["previous_commit_hash"] != last_commit["record_hash"]:
                raise RegistryCheckpointIntegrityError("checkpoint PREPARE previous commit mismatch")
            if record["old_state_root_sha256"] != last_commit["new_state_root_sha256"]:
                raise RegistryCheckpointIntegrityError("checkpoint PREPARE old root mismatch")
            pending = record
        elif record_type in {"COMMIT", "ABORT"}:
            if pending is None:
                raise RegistryCheckpointIntegrityError(
                    f"checkpoint {record_type} has no matching PREPARE"
                )
            for field in (
                "tx_id",
                "generation",
                "previous_commit_hash",
                "old_state_root_sha256",
                "new_state_root_sha256",
            ):
                if record[field] != pending[field]:
                    raise RegistryCheckpointIntegrityError(
                        f"checkpoint {record_type} does not match PREPARE"
                    )
            if record["previous_record_hash"] != pending["record_hash"]:
                raise RegistryCheckpointIntegrityError(
                    f"checkpoint {record_type} predecessor is invalid"
                )
            if record_type == "COMMIT":
                expected = expected_commit_for_prepare(pending)
                if record != expected:
                    raise RegistryCheckpointIntegrityError(
                        "checkpoint COMMIT is not the deterministic PREPARE completion"
                    )
                last_commit = record
            pending = None

        previous_record_hash = record["record_hash"]

    assert last_commit is not None
    return VerifiedCheckpointJournal(
        tail_record_hash=previous_record_hash,
        tail_sequence=int(records[-1]["sequence"]),
        last_commit=last_commit,
        pending_prepare=pending,
    )


def plan_checkpoint_recovery(
    registry: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    recovery_time: str | None = None,
) -> CheckpointRecoveryPlan:
    journal = verify_checkpoint_journal(records)
    metadata = parse_checkpoint_metadata(registry)
    state_root = registry_state_root_sha256(registry)

    if journal.pending_prepare is None:
        if metadata is None:
            raise RegistryCheckpointIntegrityError("registry checkpoint metadata is missing")
        commit = journal.last_commit
        if metadata["generation"] != commit["generation"]:
            raise RegistryCheckpointIntegrityError("registry checkpoint generation rollback detected")
        if metadata["commit_hash"] != commit["record_hash"]:
            raise RegistryCheckpointIntegrityError("registry checkpoint commit rollback detected")
        if metadata["state_root_sha256"] != commit["new_state_root_sha256"]:
            raise RegistryCheckpointIntegrityError("registry checkpoint metadata root mismatch")
        if state_root != commit["new_state_root_sha256"]:
            raise RegistryCheckpointIntegrityError("registry state rollback or tamper detected")
        return CheckpointRecoveryPlan(action="HEALTHY", journal=journal)

    prepare = journal.pending_prepare
    expected_commit = expected_commit_for_prepare(prepare)
    last_commit = journal.last_commit

    old_state_matches = (
        state_root == prepare["old_state_root_sha256"]
        and metadata is not None
        and metadata["generation"] == last_commit["generation"]
        and metadata["commit_hash"] == last_commit["record_hash"]
        and metadata["state_root_sha256"] == prepare["old_state_root_sha256"]
    )
    if old_state_matches:
        abort = make_abort_for_prepare(
            prepare,
            reason="RECOVERED_PREPARE_NOT_APPLIED",
            event_time=recovery_time,
        )
        return CheckpointRecoveryPlan(
            action="RECOVER_ABORT",
            journal=journal,
            recovery_record=abort,
        )

    new_state_matches = (
        state_root == prepare["new_state_root_sha256"]
        and metadata is not None
        and metadata["generation"] == prepare["generation"]
        and metadata["commit_hash"] == expected_commit["record_hash"]
        and metadata["state_root_sha256"] == prepare["new_state_root_sha256"]
    )
    if new_state_matches:
        return CheckpointRecoveryPlan(
            action="RECOVER_COMMIT",
            journal=journal,
            recovery_record=expected_commit,
        )

    raise RegistryCheckpointIntegrityError(
        "incomplete checkpoint PREPARE cannot be reconciled with durable registry state"
    )
