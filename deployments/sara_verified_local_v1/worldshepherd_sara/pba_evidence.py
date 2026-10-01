from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .pba_models import PBAState


PBA_EVENT_SCHEMA = "ws-pba-event-0.3"
GENESIS_HASH = "0" * 64


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


class PBAEvidenceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["ws-pba-event-0.3"] = PBA_EVENT_SCHEMA
    event_id: UUID
    mission_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=0)
    timestamp: datetime

    prior_state: PBAState
    requested_state: PBAState
    resulting_state: PBAState

    authorization_id: UUID | None = None
    permitted: bool
    rule: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=256)

    identity_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    navigation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tracking_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    interlock_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_timestamp(self) -> "PBAEvidenceEvent":
        if self.timestamp.tzinfo is None:
            raise ValueError("event timestamp must be timezone-aware")
        return self

    def unsigned_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"event_hash"})


def event_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(b"WS-PBA-EVENT-V0.3\0" + _canonical(payload)).hexdigest()


def seal_event(event: PBAEvidenceEvent) -> PBAEvidenceEvent:
    expected = event_hash(event.unsigned_payload())
    return event.model_copy(update={"event_hash": expected})


def verify_event(event: PBAEvidenceEvent, expected_previous_hash: str) -> bool:
    if event.previous_event_hash != expected_previous_hash:
        return False
    return event.event_hash == event_hash(event.unsigned_payload())


def verify_chain(events: list[PBAEvidenceEvent]) -> bool:
    """Verify a complete mission-local chain beginning at sequence zero.

    G1 deliberately validates complete chains rather than arbitrary fragments so
    prefix truncation is detectable. Future checkpoint/anchor support may add an
    explicit trusted-start mechanism for validating bounded fragments.
    """

    expected_hash = GENESIS_HASH
    expected_sequence = 0
    for event in events:
        if event.sequence != expected_sequence:
            return False
        if not verify_event(event, expected_hash):
            return False
        expected_hash = event.event_hash
        expected_sequence += 1
    return True
