from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mission_replay import MissionEvent
from .spacelink_adapter import (
    AWS_GROUND_STATION_LIST_CONTACTS_REF,
    AwsGroundStationContactAdapter,
    NormalizedSpaceContact,
    SpaceContactStatus,
)
from .spacelink_eventbridge import SpaceLinkContactProjection


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


class ReconciliationState(str, Enum):
    MATCH = "MATCH"
    PROJECTION_MISSING = "PROJECTION_MISSING"
    STALE_PROVIDER_READ = "STALE_PROVIDER_READ"
    STATUS_DIVERGENCE = "STATUS_DIVERGENCE"
    TERMINAL_CONFLICT = "TERMINAL_CONFLICT"


class SpaceLinkReconciliationRecord(BaseModel):
    """Read-only comparison between an event projection and provider read state."""

    model_config = ConfigDict(extra="forbid")

    reconciliation_id: str = Field(min_length=1)
    observed_at: datetime
    state: ReconciliationState
    provider_contact: NormalizedSpaceContact
    projection_status: SpaceContactStatus | None = None
    projection_last_event_time: datetime | None = None
    rationale: list[str] = Field(default_factory=list)
    automatic_mutation_allowed: bool = False
    authoritative_spec_ref: str = AWS_GROUND_STATION_LIST_CONTACTS_REF
    claims_scope: str = (
        "provider-read versus observed-event reconciliation only; no RF, telemetry, command, "
        "spectrum authorization, provider validation, or operational readiness is inferred"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "SpaceLinkReconciliationRecord":
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.projection_last_event_time is not None and self.projection_last_event_time.tzinfo is None:
            raise ValueError("projection_last_event_time must be timezone-aware")
        if self.automatic_mutation_allowed:
            raise ValueError("SpaceLink reconciliation is read-only in this release")
        return self

    def requires_attention(self) -> bool:
        return self.state != ReconciliationState.MATCH


class AwsGroundStationReadReconciler:
    """Compare an authoritative provider read payload with the local contact projection.

    The caller is responsible for obtaining the provider payload. This class has no AWS
    credentials, SDK client, network transport, retry loop, or provider-side write path.
    """

    reconciler_name = "aws_ground_station_read_reconciler_v1"

    def reconcile(
        self,
        *,
        reconciliation_id: str,
        projection: SpaceLinkContactProjection | None,
        provider_payload: dict[str, Any],
        observed_at: datetime,
    ) -> SpaceLinkReconciliationRecord:
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")

        provider_contact = AwsGroundStationContactAdapter().normalize_contact(provider_payload)

        if projection is None:
            return SpaceLinkReconciliationRecord(
                reconciliation_id=reconciliation_id,
                observed_at=observed_at,
                state=ReconciliationState.PROJECTION_MISSING,
                provider_contact=provider_contact,
                rationale=[
                    "Provider read returned a contact that has no local EventBridge-derived projection."
                ],
            )

        if projection.contact_id != provider_contact.contact_id:
            raise ValueError("provider read and projection refer to different contacts")

        provider_last_updated = provider_contact.last_updated
        if provider_last_updated is not None and provider_last_updated < projection.last_event_time:
            return SpaceLinkReconciliationRecord(
                reconciliation_id=reconciliation_id,
                observed_at=observed_at,
                state=ReconciliationState.STALE_PROVIDER_READ,
                provider_contact=provider_contact,
                projection_status=projection.current_status,
                projection_last_event_time=projection.last_event_time,
                rationale=[
                    "Provider read lastUpdated precedes the latest locally observed provider event; the read cannot safely overwrite the projection."
                ],
            )

        if provider_contact.status == projection.current_status:
            return SpaceLinkReconciliationRecord(
                reconciliation_id=reconciliation_id,
                observed_at=observed_at,
                state=ReconciliationState.MATCH,
                provider_contact=provider_contact,
                projection_status=projection.current_status,
                projection_last_event_time=projection.last_event_time,
                rationale=["Provider read status matches the current local projection."],
            )

        if (
            provider_contact.status in _TERMINAL_CONTACT_STATES
            and projection.current_status in _TERMINAL_CONTACT_STATES
        ):
            state = ReconciliationState.TERMINAL_CONFLICT
            rationale = [
                "Provider read and local projection disagree on terminal contact state; preserve both observations and require review."
            ]
        else:
            state = ReconciliationState.STATUS_DIVERGENCE
            rationale = [
                "Provider read and local projection disagree; best-effort event delivery means a missed or reordered provider event is possible."
            ]

        return SpaceLinkReconciliationRecord(
            reconciliation_id=reconciliation_id,
            observed_at=observed_at,
            state=state,
            provider_contact=provider_contact,
            projection_status=projection.current_status,
            projection_last_event_time=projection.last_event_time,
            rationale=rationale,
        )


def reconciliation_to_mission_event(
    record: SpaceLinkReconciliationRecord,
    *,
    sequence: int,
    t_seconds: float,
) -> MissionEvent:
    return MissionEvent(
        sequence=sequence,
        t_seconds=t_seconds,
        source="spacelink:aws_ground_station:reconciliation",
        event_type="spacelink_provider_reconciliation",
        payload={
            "reconciliation_id": record.reconciliation_id,
            "observed_at": record.observed_at.astimezone(timezone.utc).isoformat(),
            "state": record.state.value,
            "contact_id": record.provider_contact.contact_id,
            "provider_status": record.provider_contact.status.value,
            "projection_status": (
                record.projection_status.value if record.projection_status is not None else None
            ),
            "provider_last_updated": (
                record.provider_contact.last_updated.astimezone(timezone.utc).isoformat()
                if record.provider_contact.last_updated is not None
                else None
            ),
            "projection_last_event_time": (
                record.projection_last_event_time.astimezone(timezone.utc).isoformat()
                if record.projection_last_event_time is not None
                else None
            ),
            "requires_attention": record.requires_attention(),
            "automatic_mutation_allowed": record.automatic_mutation_allowed,
            "rationale": list(record.rationale),
            "claims_scope": record.claims_scope,
            "authoritative_spec_ref": record.authoritative_spec_ref,
        },
    )
