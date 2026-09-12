from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mission_replay import MissionEvent
from .spacelink_adapter import (
    AWS_GROUND_STATION_DIGITAL_TWIN_REF,
    AWS_GROUND_STATION_LIST_CONTACTS_REF,
    AwsGroundStationContactAdapter,
    ContactDisposition,
    NormalizedSpaceContact,
    SpaceContactStatus,
)


AWS_GROUND_STATION_EVENTBRIDGE_REF = (
    "https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-groundstation.html"
)
AWS_GROUND_STATION_EVENTS_REF = (
    "https://docs.aws.amazon.com/ground-station/latest/ug/monitoring.automating-events.html"
)
AWS_GROUND_STATION_EVENT_SOURCE = "aws.groundstation"
AWS_GROUND_STATION_CONTACT_DETAIL_TYPE = "Ground Station Contact State Change"

_TERMINAL_CONTACT_STATES = frozenset(
    {
        SpaceContactStatus.COMPLETED,
        SpaceContactStatus.FAILED,
        SpaceContactStatus.FAILED_TO_SCHEDULE,
        SpaceContactStatus.CANCELLED,
        SpaceContactStatus.AWS_CANCELLED,
        SpaceContactStatus.AWS_FAILED,
    }
)


class NormalizedGroundStationEvent(BaseModel):
    """Claims-controlled normalized AWS Ground Station contact event.

    AWS documents these service events as EventBridge events delivered on a
    best-effort basis. A normalized event therefore proves only that a payload
    matching the documented event contract was ingested. It does not prove a
    complete event history, RF execution, telemetry delivery, or spacecraft
    command delivery.
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["AWS_GROUND_STATION"] = "AWS_GROUND_STATION"
    provider_event_id: str = Field(min_length=1)
    event_time: datetime
    region: str = Field(min_length=1)
    account: str | None = None
    resources: list[str] = Field(default_factory=list)
    contact: NormalizedSpaceContact
    mission_profile_ref: str | None = None
    satellite_ref: str | None = None
    delivery_semantics: Literal["BEST_EFFORT"] = "BEST_EFFORT"
    authoritative_spec_ref: str = AWS_GROUND_STATION_EVENTS_REF

    @model_validator(mode="after")
    def require_timezone(self) -> "NormalizedGroundStationEvent":
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        return self

    def claims_boundary(self) -> str:
        return (
            "Normalized provider event evidence only; EventBridge Ground Station service "
            "events are best-effort, so completeness is not inferred. No RF, telemetry, "
            "spacecraft command, provider validation, or operational readiness is claimed."
        )


class AwsGroundStationEventBridgeAdapter:
    """Normalize documented Ground Station contact-state EventBridge payloads.

    This adapter performs local schema validation only. It does not create an
    EventBridge rule, consume an AWS account, invoke Lambda, reserve a contact,
    or execute any provider-side action.
    """

    adapter_name = "aws_ground_station_eventbridge_contact_v1"

    def normalize_event(self, payload: dict[str, Any]) -> NormalizedGroundStationEvent:
        source = payload.get("source")
        if source != AWS_GROUND_STATION_EVENT_SOURCE:
            raise ValueError(
                f"unexpected EventBridge source: {source!r}; expected {AWS_GROUND_STATION_EVENT_SOURCE!r}"
            )

        detail_type = payload.get("detail-type", payload.get("detailType"))
        if detail_type != AWS_GROUND_STATION_CONTACT_DETAIL_TYPE:
            raise ValueError(
                "unexpected EventBridge detail type for SpaceLink contact ingestion"
            )

        event_id = payload.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("EventBridge payload lacks a non-empty id")

        event_time = _coerce_event_time(payload.get("time"))

        region = payload.get("region")
        if not isinstance(region, str) or not region:
            raise ValueError("EventBridge payload lacks a non-empty region")

        detail = payload.get("detail")
        if not isinstance(detail, dict):
            raise ValueError("EventBridge payload detail must be an object")

        contact_id = detail.get("contactId")
        status = detail.get("contactStatus")
        if not isinstance(contact_id, str) or not contact_id:
            raise ValueError("Ground Station contact event lacks contactId")
        if status is None:
            raise ValueError("Ground Station contact event lacks contactStatus")

        contact_payload: dict[str, Any] = {
            "contactId": contact_id,
            "contactStatus": status,
            "groundStation": detail.get("groundstationId", detail.get("groundStation")),
            "lastUpdated": event_time,
        }
        contact = AwsGroundStationContactAdapter().normalize_contact(contact_payload)

        resources_raw = payload.get("resources", [])
        if resources_raw is None:
            resources_raw = []
        if not isinstance(resources_raw, list):
            raise ValueError("EventBridge resources must be a list")

        account = payload.get("account")
        if account is not None and not isinstance(account, str):
            raise ValueError("EventBridge account must be a string when present")

        return NormalizedGroundStationEvent(
            provider_event_id=event_id,
            event_time=event_time,
            region=region,
            account=account,
            resources=[str(item) for item in resources_raw],
            contact=contact,
            mission_profile_ref=_optional_str(detail.get("missionProfileArn")),
            satellite_ref=_optional_str(detail.get("satelliteArn")),
        )


class SpaceLinkContactProjection(BaseModel):
    """Read-only OVERWATCH-facing projection for one contact.

    The projection is deterministic and idempotent by provider event ID. It is
    intentionally conservative about ordering: an older event cannot overwrite
    a newer observation, and a terminal provider state cannot transition to a
    different state inside this projection.
    """

    model_config = ConfigDict(extra="forbid")

    contact_id: str = Field(min_length=1)
    current_status: SpaceContactStatus
    disposition: ContactDisposition
    ground_station: str | None = None
    region: str = Field(min_length=1)
    mission_profile_ref: str | None = None
    satellite_ref: str | None = None
    first_event_time: datetime
    last_event_time: datetime
    last_event_id: str = Field(min_length=1)
    applied_event_ids: list[str] = Field(default_factory=list, max_length=64)
    event_count: int = Field(ge=1)
    terminal: bool
    delivery_semantics: Literal["BEST_EFFORT"] = "BEST_EFFORT"
    claims_scope: Literal[
        "provider-event projection only; completeness and RF/telemetry/command execution not established"
    ] = "provider-event projection only; completeness and RF/telemetry/command execution not established"

    @model_validator(mode="after")
    def validate_projection(self) -> "SpaceLinkContactProjection":
        if self.first_event_time.tzinfo is None or self.last_event_time.tzinfo is None:
            raise ValueError("projection timestamps must be timezone-aware")
        if self.last_event_time < self.first_event_time:
            raise ValueError("last_event_time cannot precede first_event_time")
        if self.last_event_id not in self.applied_event_ids:
            raise ValueError("last_event_id must be present in applied_event_ids")
        if self.terminal != (self.current_status in _TERMINAL_CONTACT_STATES):
            raise ValueError("terminal flag does not match current_status")
        return self

    def overwatch_snapshot(self) -> dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "status": self.current_status.value,
            "disposition": self.disposition.value,
            "ground_station": self.ground_station,
            "region": self.region,
            "mission_profile_ref": self.mission_profile_ref,
            "satellite_ref": self.satellite_ref,
            "first_event_time": self.first_event_time.astimezone(timezone.utc).isoformat(),
            "last_event_time": self.last_event_time.astimezone(timezone.utc).isoformat(),
            "last_event_id": self.last_event_id,
            "event_count": self.event_count,
            "terminal": self.terminal,
            "delivery_semantics": self.delivery_semantics,
            "claims_scope": self.claims_scope,
        }


def apply_contact_event(
    state: SpaceLinkContactProjection | None,
    event: NormalizedGroundStationEvent,
) -> SpaceLinkContactProjection:
    """Apply a normalized contact event with deterministic fail-closed rules."""

    contact = event.contact
    if state is None:
        return SpaceLinkContactProjection(
            contact_id=contact.contact_id,
            current_status=contact.status,
            disposition=contact.disposition,
            ground_station=contact.ground_station,
            region=event.region,
            mission_profile_ref=event.mission_profile_ref,
            satellite_ref=event.satellite_ref,
            first_event_time=event.event_time,
            last_event_time=event.event_time,
            last_event_id=event.provider_event_id,
            applied_event_ids=[event.provider_event_id],
            event_count=1,
            terminal=contact.status in _TERMINAL_CONTACT_STATES,
        )

    if state.contact_id != contact.contact_id:
        raise ValueError("contact projection cannot ingest an event for another contact")

    if event.provider_event_id in state.applied_event_ids:
        return state

    if event.event_time < state.last_event_time:
        raise ValueError("out-of-order provider event would overwrite newer contact state")

    if state.terminal and contact.status != state.current_status:
        raise ValueError("terminal contact state cannot transition to a different state")

    ids = [*state.applied_event_ids, event.provider_event_id]
    if len(ids) > 64:
        ids = ids[-64:]

    return state.model_copy(
        update={
            "current_status": contact.status,
            "disposition": contact.disposition,
            "ground_station": contact.ground_station or state.ground_station,
            "region": event.region,
            "mission_profile_ref": event.mission_profile_ref or state.mission_profile_ref,
            "satellite_ref": event.satellite_ref or state.satellite_ref,
            "last_event_time": event.event_time,
            "last_event_id": event.provider_event_id,
            "applied_event_ids": ids,
            "event_count": state.event_count + 1,
            "terminal": contact.status in _TERMINAL_CONTACT_STATES,
        }
    )


def event_to_mission_event(
    event: NormalizedGroundStationEvent,
    *,
    sequence: int,
    t_seconds: float,
) -> MissionEvent:
    return MissionEvent(
        sequence=sequence,
        t_seconds=t_seconds,
        source="spacelink:aws_ground_station:eventbridge",
        event_type="spacelink_provider_contact_event",
        payload={
            "provider_event_id": event.provider_event_id,
            "event_time": event.event_time.astimezone(timezone.utc).isoformat(),
            "contact_id": event.contact.contact_id,
            "contact_status": event.contact.status.value,
            "disposition": event.contact.disposition.value,
            "ground_station": event.contact.ground_station,
            "region": event.region,
            "mission_profile_ref": event.mission_profile_ref,
            "satellite_ref": event.satellite_ref,
            "delivery_semantics": event.delivery_semantics,
            "authoritative_spec_ref": event.authoritative_spec_ref,
        },
    )


def digital_twin_event_claims_boundary(event: NormalizedGroundStationEvent) -> str:
    """Return the conservative claim for an event from a named digital-twin station."""

    station = event.contact.ground_station or ""
    if not station.startswith("Digital Twin "):
        raise ValueError("event is not identified as an AWS Ground Station digital-twin station")
    return (
        "Digital-twin API/event behavior only; AWS documents that digital-twin ground stations "
        "do not currently support data delivery or telemetry delivery. No RF, downlink, telemetry, "
        "or spacecraft-command delivery is inferred. "
        f"Reference: {AWS_GROUND_STATION_DIGITAL_TWIN_REF}"
    )


def _coerce_event_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("EventBridge time must be a timezone-aware datetime string")
    if result.tzinfo is None:
        raise ValueError("EventBridge time must include a timezone")
    return result


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
