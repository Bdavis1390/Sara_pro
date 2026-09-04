from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .hmaa import (
    AssuranceAssessment,
    HMAAEvent,
    event_identity_key,
    event_source_fingerprint,
    evaluate_event_assurance,
)


class ReplayObservation(BaseModel):
    deduplication_key: str
    source_fingerprint: str
    duplicate_event: bool = False
    conflicting_replay: bool = False


class ChronologyObservation(BaseModel):
    scope_key: str
    previous_latest_source_timestamp: datetime | None = None
    skew_seconds: float = 0.0
    out_of_order_event: bool = False


class HMAAStateObservation(BaseModel):
    replay: ReplayObservation
    chronology: ChronologyObservation


class HMAAAssuranceState:
    def __init__(self, clock_skew_tolerance_seconds: float = 2.0) -> None:
        if clock_skew_tolerance_seconds < 0:
            raise ValueError("clock skew tolerance must be non-negative")
        self.clock_skew_tolerance_seconds = float(clock_skew_tolerance_seconds)
        self._seen_fingerprints: dict[str, str] = {}
        self._latest_source_timestamps: dict[str, datetime] = {}

    @staticmethod
    def _chronology_scope(event: HMAAEvent) -> str:
        subject = event.entity_id or event.task_id or "mission"
        return "\x1f".join((event.mission_id, event.source_system, subject))

    def observe(self, event: HMAAEvent) -> HMAAStateObservation:
        identity = event_identity_key(event)
        fingerprint = event_source_fingerprint(event)
        prior_fingerprint = self._seen_fingerprints.get(identity)

        duplicate = prior_fingerprint == fingerprint if prior_fingerprint else False
        conflicting = (
            prior_fingerprint is not None and prior_fingerprint != fingerprint
        )
        if prior_fingerprint is None:
            self._seen_fingerprints[identity] = fingerprint

        scope = self._chronology_scope(event)
        previous_latest = self._latest_source_timestamps.get(scope)
        skew_seconds = 0.0
        out_of_order = False

        if previous_latest is not None:
            skew_seconds = max(
                0.0,
                (previous_latest - event.source_timestamp).total_seconds(),
            )
            out_of_order = skew_seconds > self.clock_skew_tolerance_seconds

        if previous_latest is None or event.source_timestamp > previous_latest:
            self._latest_source_timestamps[scope] = event.source_timestamp

        return HMAAStateObservation(
            replay=ReplayObservation(
                deduplication_key=identity,
                source_fingerprint=fingerprint,
                duplicate_event=duplicate,
                conflicting_replay=conflicting,
            ),
            chronology=ChronologyObservation(
                scope_key=scope,
                previous_latest_source_timestamp=previous_latest,
                skew_seconds=skew_seconds,
                out_of_order_event=out_of_order,
            ),
        )

    def assess(
        self,
        event: HMAAEvent,
        *,
        connection_healthy: bool = True,
        policy_engine_available: bool = True,
        checksum_valid: bool = True,
    ) -> tuple[HMAAStateObservation, AssuranceAssessment]:
        observation = self.observe(event)
        assessment = evaluate_event_assurance(
            connection_healthy=connection_healthy,
            policy_engine_available=policy_engine_available,
            duplicate_event=observation.replay.duplicate_event,
            conflicting_replay=observation.replay.conflicting_replay,
            out_of_order_event=observation.chronology.out_of_order_event,
            checksum_valid=checksum_valid,
        )
        return observation, assessment

    def snapshot(self) -> dict[str, Any]:
        return {
            "clock_skew_tolerance_seconds": self.clock_skew_tolerance_seconds,
            "deduplication_identities": len(self._seen_fingerprints),
            "chronology_scopes": len(self._latest_source_timestamps),
        }
