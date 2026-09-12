from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mission_replay import MissionEvent


AWS_GROUND_STATION_API_REF = (
    "https://docs.aws.amazon.com/ground-station/latest/APIReference/Welcome.html"
)
AWS_GROUND_STATION_LIST_CONTACTS_REF = (
    "https://docs.aws.amazon.com/ground-station/latest/APIReference/API_ListContacts.html"
)
AWS_GROUND_STATION_RESERVE_CONTACT_REF = (
    "https://docs.aws.amazon.com/ground-station/latest/APIReference/API_ReserveContact.html"
)
AWS_GROUND_STATION_DIGITAL_TWIN_REF = (
    "https://docs.aws.amazon.com/ground-station/latest/ug/digital-twin.html"
)


class SpaceContactStatus(str, Enum):
    """Contact states documented by the AWS Ground Station API.

    These values describe a provider contact lifecycle. They do not imply that
    Worldshepherd controls RF equipment, owns spectrum rights, or has completed
    an operational satellite integration.
    """

    SCHEDULING = "SCHEDULING"
    FAILED_TO_SCHEDULE = "FAILED_TO_SCHEDULE"
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    AWS_CANCELLED = "AWS_CANCELLED"
    PREPASS = "PREPASS"
    PASS = "PASS"
    POSTPASS = "POSTPASS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AVAILABLE = "AVAILABLE"
    CANCELLING = "CANCELLING"
    AWS_FAILED = "AWS_FAILED"


class ContactDisposition(str, Enum):
    AVAILABLE = "AVAILABLE"
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    SUCCEEDED = "SUCCEEDED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


_DISPOSITION_BY_STATUS: dict[SpaceContactStatus, ContactDisposition] = {
    SpaceContactStatus.AVAILABLE: ContactDisposition.AVAILABLE,
    SpaceContactStatus.SCHEDULING: ContactDisposition.PENDING,
    SpaceContactStatus.CANCELLING: ContactDisposition.PENDING,
    SpaceContactStatus.SCHEDULED: ContactDisposition.SCHEDULED,
    SpaceContactStatus.PREPASS: ContactDisposition.ACTIVE,
    SpaceContactStatus.PASS: ContactDisposition.ACTIVE,
    SpaceContactStatus.POSTPASS: ContactDisposition.ACTIVE,
    SpaceContactStatus.COMPLETED: ContactDisposition.SUCCEEDED,
    SpaceContactStatus.CANCELLED: ContactDisposition.CANCELLED,
    SpaceContactStatus.AWS_CANCELLED: ContactDisposition.CANCELLED,
    SpaceContactStatus.FAILED_TO_SCHEDULE: ContactDisposition.FAILED,
    SpaceContactStatus.FAILED: ContactDisposition.FAILED,
    SpaceContactStatus.AWS_FAILED: ContactDisposition.FAILED,
}


class NormalizedSpaceContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    contact_id: str = Field(min_length=1)
    status: SpaceContactStatus
    disposition: ContactDisposition
    version_id: int | None = Field(default=None, ge=1)
    ground_station: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    last_updated: datetime | None = None
    failure_codes: list[str] = Field(default_factory=list)
    failure_message: str | None = None
    authoritative_spec_ref: str = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contact_window(self) -> "NormalizedSpaceContact":
        for label, value in (
            ("start_time", self.start_time),
            ("end_time", self.end_time),
            ("last_updated", self.last_updated),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{label} must be timezone-aware")
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
        expected = _DISPOSITION_BY_STATUS[self.status]
        if self.disposition != expected:
            raise ValueError(
                f"disposition {self.disposition.value} does not match status {self.status.value}"
            )
        return self


class GroundNetworkContactAdapter(Protocol):
    adapter_name: str

    def normalize_contact(self, payload: dict[str, Any]) -> NormalizedSpaceContact:
        ...


class SyntheticGroundNetworkAdapter:
    """Adapter for frozen, non-RF test fixtures only."""

    adapter_name = "spacelink_synthetic_fixture_v1"

    def normalize_contact(self, payload: dict[str, Any]) -> NormalizedSpaceContact:
        status = _status_from_value(payload["status"])
        return NormalizedSpaceContact(
            provider=str(payload.get("provider", "SYNTHETIC")),
            contact_id=str(payload["contact_id"]),
            status=status,
            disposition=_DISPOSITION_BY_STATUS[status],
            version_id=_optional_int(payload.get("version_id")),
            ground_station=_optional_str(payload.get("ground_station")),
            start_time=_coerce_datetime(payload.get("start_time")),
            end_time=_coerce_datetime(payload.get("end_time")),
            last_updated=_coerce_datetime(payload.get("last_updated")),
            failure_codes=_string_list(payload.get("failure_codes", [])),
            failure_message=_optional_str(payload.get("failure_message")),
            authoritative_spec_ref="fixture://spacelink-synthetic-v1",
            attributes={"claims_scope": "synthetic fixture only"},
        )


class AwsGroundStationContactAdapter:
    """Normalize documented AWS Ground Station contact response fields.

    This adapter performs schema normalization only. It makes no AWS API call,
    reserves no contact, transmits no command, receives no telemetry, and does
    not establish partner validation or operational interoperability.
    """

    adapter_name = "aws_ground_station_contact_schema_v1"

    def normalize_contact(self, payload: dict[str, Any]) -> NormalizedSpaceContact:
        raw_status = payload.get("contactStatus", payload.get("status"))
        if raw_status is None:
            raise ValueError("AWS Ground Station contact payload lacks contactStatus/status")
        status = _status_from_value(raw_status)
        contact_id = payload.get("contactId")
        if not isinstance(contact_id, str) or not contact_id:
            raise ValueError("AWS Ground Station contact payload lacks contactId")

        version_id = payload.get("versionId")
        if version_id is None and isinstance(payload.get("version"), dict):
            version_id = payload["version"].get("versionId")

        return NormalizedSpaceContact(
            provider="AWS_GROUND_STATION",
            contact_id=contact_id,
            status=status,
            disposition=_DISPOSITION_BY_STATUS[status],
            version_id=_optional_int(version_id),
            ground_station=_optional_str(payload.get("groundStation")),
            start_time=_coerce_datetime(payload.get("startTime")),
            end_time=_coerce_datetime(payload.get("endTime")),
            last_updated=_coerce_datetime(payload.get("lastUpdated")),
            failure_codes=_string_list(payload.get("failureCodes", [])),
            failure_message=_optional_str(
                payload.get("failureMessage", payload.get("errorMessage"))
            ),
            authoritative_spec_ref=AWS_GROUND_STATION_LIST_CONTACTS_REF,
            attributes={
                "adapter_name": self.adapter_name,
                "status_field": (
                    "contactStatus" if "contactStatus" in payload else "status"
                ),
            },
        )


class ContactReservationProposal(BaseModel):
    """Non-executable contact-reservation proposal.

    v0.1 intentionally stops at a human-authority boundary. A future provider
    executor must add explicit PRIME authorization and its own validated
    credential/idempotency controls before any provider write can occur.
    """

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    provider: Literal["AWS_GROUND_STATION"] = "AWS_GROUND_STATION"
    start_time: datetime
    end_time: datetime
    ground_station: str = Field(min_length=1)
    mission_profile_ref: str = Field(min_length=1)
    satellite_ref: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    authority_required: Literal["identified-human-authority"] = "identified-human-authority"
    execution_allowed: Literal[False] = False
    authoritative_spec_ref: str = AWS_GROUND_STATION_RESERVE_CONTACT_REF

    @model_validator(mode="after")
    def validate_window(self) -> "ContactReservationProposal":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("reservation times must be timezone-aware")
        if self.end_time <= self.start_time:
            raise ValueError("reservation end_time must be after start_time")
        return self

    def provider_request_preview(self) -> dict[str, Any]:
        """Return documented ReserveContact field names without executing them."""
        return {
            "startTime": self.start_time.astimezone(timezone.utc).isoformat(),
            "endTime": self.end_time.astimezone(timezone.utc).isoformat(),
            "groundStation": self.ground_station,
            "missionProfileArn": self.mission_profile_ref,
            "satelliteArn": self.satellite_ref,
        }

    def claims_boundary(self) -> str:
        return (
            "Proposal/schema evidence only; no AWS contact reservation, RF transmission, "
            "spectrum authorization, telemetry delivery, partner validation, or operational "
            "satellite integration is claimed."
        )


class AwsDigitalTwinCapabilityBoundary(BaseModel):
    """Current capability boundary from the AWS Ground Station user guide."""

    provider: Literal["AWS_GROUND_STATION"] = "AWS_GROUND_STATION"
    scheduling_api_test: Literal[True] = True
    configuration_verification: Literal[True] = True
    error_handling_test: Literal[True] = True
    production_antenna_capacity_required: Literal[False] = False
    spectrum_license_required_for_digital_twin_api_test: Literal[False] = False
    data_delivery_supported: Literal[False] = False
    telemetry_delivery_supported: Literal[False] = False
    authoritative_spec_ref: str = AWS_GROUND_STATION_DIGITAL_TWIN_REF


AWS_DIGITAL_TWIN_BOUNDARY = AwsDigitalTwinCapabilityBoundary()


def contact_to_mission_event(
    contact: NormalizedSpaceContact,
    *,
    sequence: int,
    t_seconds: float,
) -> MissionEvent:
    return MissionEvent(
        sequence=sequence,
        t_seconds=t_seconds,
        source=f"spacelink:{contact.provider.lower()}",
        event_type="spacelink_contact_state",
        payload={
            "contact_id": contact.contact_id,
            "status": contact.status.value,
            "disposition": contact.disposition.value,
            "version_id": contact.version_id,
            "ground_station": contact.ground_station,
            "failure_codes": contact.failure_codes,
            "failure_message": contact.failure_message,
            "authoritative_spec_ref": contact.authoritative_spec_ref,
        },
    )


def _status_from_value(value: Any) -> SpaceContactStatus:
    try:
        return SpaceContactStatus(str(value))
    except ValueError as exc:
        raise ValueError(f"unrecognized space-contact status: {value!r}") from exc


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    result = int(value)
    if result < 1:
        raise ValueError("version id must be >= 1")
    return result


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError("failure codes must be a list")
    return [str(item) for item in value]


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("datetime strings must include a timezone")
        return parsed
    raise ValueError(f"unsupported datetime value: {type(value).__name__}")
