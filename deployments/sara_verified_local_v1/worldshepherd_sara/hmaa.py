from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


HMAA_SCHEMA_VERSION = "worldshepherd.hmaa.evidence.v0.1"


class AssuranceDisposition(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    REVIEW = "REVIEW"
    INDETERMINATE = "INDETERMINATE"


class HMAAEvent(BaseModel):
    schema_version: str = HMAA_SCHEMA_VERSION
    event_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    source_system: str = Field(default="lattice", min_length=1)
    entity_id: str | None = None
    task_id: str | None = None
    event_type: str = Field(min_length=1)
    source_timestamp: datetime
    ingest_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str | None = None
    event_hash: str | None = None


class AssuranceAssessment(BaseModel):
    disposition: AssuranceDisposition
    reasons: list[str] = Field(default_factory=list)


class HMAAEvidenceBundle(BaseModel):
    schema_version: str = HMAA_SCHEMA_VERSION
    mission_id: str = Field(min_length=1)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    events: list[HMAAEvent] = Field(default_factory=list)
    final_chain_hash: str | None = None


def canonical_event_bytes(event: HMAAEvent) -> bytes:
    body = event.model_dump(mode="json", exclude={"event_hash"})
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def seal_event(event: HMAAEvent, previous_event_hash: str | None = None) -> HMAAEvent:
    candidate = event.model_copy(
        update={
            "previous_event_hash": previous_event_hash,
            "event_hash": None,
        }
    )
    digest = hashlib.sha256(canonical_event_bytes(candidate)).hexdigest()
    return candidate.model_copy(update={"event_hash": f"sha256:{digest}"})


def verify_chain(events: list[HMAAEvent]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected_previous: str | None = None

    for index, event in enumerate(events):
        if event.previous_event_hash != expected_previous:
            errors.append(
                f"event[{index}] previous_event_hash does not match chain head"
            )

        candidate = event.model_copy(
            update={
                "previous_event_hash": expected_previous,
                "event_hash": None,
            }
        )
        expected_hash = (
            "sha256:" + hashlib.sha256(canonical_event_bytes(candidate)).hexdigest()
        )
        if event.event_hash != expected_hash:
            errors.append(f"event[{index}] event_hash verification failed")

        expected_previous = event.event_hash

    return not errors, errors


def evaluate_event_assurance(
    *,
    connection_healthy: bool = True,
    policy_engine_available: bool = True,
    duplicate_event: bool = False,
    out_of_order_event: bool = False,
    checksum_valid: bool = True,
) -> AssuranceAssessment:
    if not policy_engine_available:
        return AssuranceAssessment(
            disposition=AssuranceDisposition.INDETERMINATE,
            reasons=["policy engine unavailable; approval must not be inferred"],
        )

    review_reasons: list[str] = []
    warning_reasons: list[str] = []

    if not checksum_valid:
        review_reasons.append("evidence checksum validation failed")
    if out_of_order_event:
        review_reasons.append("event chronology is out of order")
    if duplicate_event:
        warning_reasons.append("duplicate event detected; deduplication required")
    if not connection_healthy:
        warning_reasons.append("source connection heartbeat is degraded")

    if review_reasons:
        return AssuranceAssessment(
            disposition=AssuranceDisposition.REVIEW,
            reasons=review_reasons + warning_reasons,
        )
    if warning_reasons:
        return AssuranceAssessment(
            disposition=AssuranceDisposition.WARN,
            reasons=warning_reasons,
        )
    return AssuranceAssessment(
        disposition=AssuranceDisposition.ALLOW,
        reasons=["no assurance exception detected"],
    )


def build_evidence_bundle(
    mission_id: str, events: list[HMAAEvent]
) -> HMAAEvidenceBundle:
    ok, errors = verify_chain(events)
    if not ok:
        raise ValueError("invalid HMAA evidence chain: " + "; ".join(errors))
    if any(event.mission_id != mission_id for event in events):
        raise ValueError("all HMAA events must match the evidence-bundle mission_id")
    return HMAAEvidenceBundle(
        mission_id=mission_id,
        events=events,
        final_chain_hash=events[-1].event_hash if events else None,
    )
