from __future__ import annotations

from collections import Counter
from typing import Any
from pydantic import BaseModel, Field

from .echo_checkpoint_verify import verify_bundle
from .echo_event_store import EchoEventStore, EchoIngestResult, EchoStoredEvent, semantic_sha256
from .improvement_ledger import ImprovementLedger
from .models import AuditRecord
from .qualification import canonical_digest

LEDGER_CHECKPOINT_SCHEMA = "WS-RI-LEDGER-CHECKPOINT-V1"
LEDGER_ECHO_EVENT_SCHEMA = "WS-RI-LEDGER-ECHO-ANCHOR-V1"
_LEDGER_PAYLOAD_KEY = "_ws_ri_ledger_checkpoint"

class ImprovementCheckpointError(RuntimeError):
    pass

class ImprovementLedgerCheckpoint(BaseModel):
    schema: str = LEDGER_CHECKPOINT_SCHEMA
    record_count: int = Field(ge=1)
    head_sequence: int = Field(ge=1)
    head_record_digest: str = Field(min_length=1)
    state_counts: dict[str, int]
    created_utc: str = Field(min_length=1)
    claims_boundary: str = Field(min_length=1)
    checkpoint_digest: str = Field(min_length=1)

def _payload(record_count: int, head_sequence: int, head_record_digest: str, state_counts: dict[str, int], created_utc: str) -> dict[str, Any]:
    return {
        "schema": LEDGER_CHECKPOINT_SCHEMA,
        "record_count": record_count,
        "head_sequence": head_sequence,
        "head_record_digest": head_record_digest,
        "state_counts": dict(sorted(state_counts.items())),
        "created_utc": created_utc,
        "claims_boundary": "local WS-RI custody digest only; stronger retention or deployment claims require separate evidence",
    }

def build_ledger_checkpoint(ledger: ImprovementLedger, *, created_utc: str) -> ImprovementLedgerCheckpoint:
    if not created_utc.strip():
        raise ImprovementCheckpointError("created_utc is required")
    if not ledger.verify_chain():
        raise ImprovementCheckpointError("WS-RI ledger chain verification failed")
    records = ledger.records()
    if not records:
        raise ImprovementCheckpointError("cannot checkpoint an empty WS-RI ledger")
    head = records[-1]
    material = _payload(len(records), head.sequence, head.record_digest, dict(Counter(r.state for r in records)), created_utc.strip())
    return ImprovementLedgerCheckpoint(**material, checkpoint_digest=canonical_digest(material))

def build_ledger_checkpoint_event(ledger: ImprovementLedger, *, event_id: str, actor: str, timestamp: str) -> tuple[AuditRecord, ImprovementLedgerCheckpoint]:
    if not event_id.strip() or not actor.strip() or not timestamp.strip():
        raise ImprovementCheckpointError("event_id, actor, and timestamp are required")
    checkpoint = build_ledger_checkpoint(ledger, created_utc=timestamp)
    record = AuditRecord(
        timestamp=timestamp,
        event="ws_ri_ledger_checkpoint",
        actor=actor,
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            _LEDGER_PAYLOAD_KEY: checkpoint.model_dump(mode="json"),
            "anchor_schema": LEDGER_ECHO_EVENT_SCHEMA,
        },
    )
    semantic_sha256(record)
    return record, checkpoint

def ingest_ledger_checkpoint_into_echo(store: EchoEventStore, ledger: ImprovementLedger, *, event_id: str, actor: str, timestamp: str) -> tuple[EchoIngestResult, ImprovementLedgerCheckpoint]:
    record, checkpoint = build_ledger_checkpoint_event(ledger, event_id=event_id, actor=actor, timestamp=timestamp)
    return store.ingest(record), checkpoint

def verify_stored_ledger_checkpoint(stored: EchoStoredEvent, expected: ImprovementLedgerCheckpoint) -> bool:
    try:
        record = AuditRecord(timestamp=stored.first_audit_timestamp, event=stored.event, actor=stored.actor, payload=stored.payload())
        if semantic_sha256(record) != stored.semantic_sha256:
            return False
        raw = record.payload.get(_LEDGER_PAYLOAD_KEY)
        if not isinstance(raw, dict):
            return False
        observed = ImprovementLedgerCheckpoint.model_validate(raw)
        if observed != expected:
            return False
        material = observed.model_dump(mode="json")
        digest = material.pop("checkpoint_digest")
        return digest == canonical_digest(material)
    except Exception:
        return False

def verify_signed_echo_membership(bundle: dict[str, Any], *, trusted_fingerprint_sha256: str, event_id: str, semantic_digest: str) -> dict[str, Any]:
    summary = verify_bundle(bundle, trusted_fingerprint_sha256)
    manifest = bundle.get("manifest")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("events"), list):
        raise ImprovementCheckpointError("verified ECHO bundle has no membership list")
    matches = [item for item in manifest["events"] if isinstance(item, dict) and item.get("event_id") == event_id and item.get("semantic_sha256") == semantic_digest]
    if len(matches) != 1:
        raise ImprovementCheckpointError("WS-RI ledger anchor is not uniquely present in the verified ECHO checkpoint")
    return {
        "status": "PASS",
        "event_id": event_id,
        "semantic_sha256": semantic_digest,
        "echo_checkpoint_id": manifest.get("checkpoint_id"),
        "echo_checkpoint_sha256": bundle.get("checkpoint_sha256"),
        "echo_verification": summary,
    }
