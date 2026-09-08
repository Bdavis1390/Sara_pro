from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .mission_replay import MissionEvent, replay_events
from .sensor_fusion import Observation, fuse_observations


CLAIMS_BOUNDARY = (
    "SYNTHETIC/UNCLASSIFIED SOFTWARE DEMONSTRATION ONLY; NOT BAE-, SDA-, SSC-, "
    "SPACE FORCE-, OR GOLDEN DOME-VALIDATED; NOT AN OPERATIONAL TRACKER, FIRE-CONTROL, "
    "WEAPON-CUEING, OR ENGAGEMENT SYSTEM."
)

ALLOWED_ACTION = "advisory_dissemination"
BLOCKED_ACTIONS = {
    "fire_control_cue",
    "weapon_cue",
    "engage",
    "intercept",
    "launch",
    "target_designation",
}


class ProvenancedObservation(BaseModel):
    observation_id: str = Field(min_length=1)
    sensor_id: str = Field(min_length=1)
    t_seconds: float = Field(ge=0.0)
    x: float
    y: float
    confidence: float = Field(ge=0.0, le=1.0)
    source_sha256: str = Field(min_length=64, max_length=64)
    source_status: Literal["synthetic", "synthetic_fault_injected"] = "synthetic"

    @field_validator("source_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        lowered = value.lower()
        if any(character not in "0123456789abcdef" for character in lowered):
            raise ValueError("source_sha256 must be a hexadecimal SHA-256 digest")
        return lowered

    def as_fusion_observation(self) -> Observation:
        return Observation(
            observation_id=self.observation_id,
            sensor_id=self.sensor_id,
            t_seconds=self.t_seconds,
            x=self.x,
            y=self.y,
            confidence=self.confidence,
        )


class RMABMPolicy(BaseModel):
    min_track_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    min_independent_sensors: int = Field(default=2, ge=1)
    max_observation_age_seconds: float = Field(default=8.0, gt=0.0)
    require_identified_human_authority: bool = True
    permitted_action: Literal["advisory_dissemination"] = ALLOWED_ACTION


class TrackDecision(BaseModel):
    track_id: str
    decision: Literal["AUTHORIZED_ADVISORY", "HOLD", "BLOCK"]
    requested_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    independent_sensor_count: int = Field(ge=0)
    source_observation_ids: list[str]
    source_sensor_ids: list[str]
    reasons: list[str]
    human_authority: str | None = None


class RMABMMetrics(BaseModel):
    provenance_completeness: float = Field(ge=0.0, le=1.0)
    policy_enforcement_rate: float = Field(ge=0.0, le=1.0)
    stale_observation_traceability: float = Field(ge=0.0, le=1.0)
    degraded_state_continuity: bool
    deterministic_replay_digest: str = Field(min_length=64, max_length=64)


class RMABMResult(BaseModel):
    scenario_id: str
    evidence_state: Literal["IMPLEMENTED_IN_SOFTWARE_SYNTHETIC_ONLY"]
    claims_boundary: str
    ordered_event_sequences: list[int]
    stale_observation_ids: list[str]
    fresh_observation_ids: list[str]
    decisions: list[TrackDecision]
    metrics: RMABMMetrics
    audit_sha256: str = Field(min_length=64, max_length=64)


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_requested_action(requested_action: str) -> None:
    normalized = requested_action.strip().lower()
    if normalized in BLOCKED_ACTIONS:
        return
    if normalized != ALLOWED_ACTION:
        raise ValueError(
            f"unsupported requested_action={requested_action!r}; synthetic G1 permits only {ALLOWED_ACTION!r}"
        )


def _decision_for_track(
    *,
    track: Any,
    policy: RMABMPolicy,
    requested_action: str,
    human_authority: str | None,
) -> TrackDecision:
    normalized_action = requested_action.strip().lower()
    reasons: list[str] = []

    if normalized_action in BLOCKED_ACTIONS:
        return TrackDecision(
            track_id=track.track_id,
            decision="BLOCK",
            requested_action=requested_action,
            confidence=track.confidence,
            independent_sensor_count=len(track.source_sensor_ids),
            source_observation_ids=list(track.source_observation_ids),
            source_sensor_ids=list(track.source_sensor_ids),
            reasons=["G1 claims/safety boundary prohibits fire-control, weapon cueing, engagement, launch, or target designation."],
            human_authority=human_authority,
        )

    if track.confidence < policy.min_track_confidence:
        reasons.append(
            f"track confidence {track.confidence:.3f} below threshold {policy.min_track_confidence:.3f}"
        )
    if len(track.source_sensor_ids) < policy.min_independent_sensors:
        reasons.append(
            f"independent sensor count {len(track.source_sensor_ids)} below threshold {policy.min_independent_sensors}"
        )
    if policy.require_identified_human_authority and not human_authority:
        reasons.append("identified human authority is required for advisory dissemination")

    if reasons:
        decision = "HOLD"
    else:
        decision = "AUTHORIZED_ADVISORY"
        reasons.append("synthetic advisory release gates satisfied; no engagement authority is conveyed")

    return TrackDecision(
        track_id=track.track_id,
        decision=decision,
        requested_action=requested_action,
        confidence=track.confidence,
        independent_sensor_count=len(track.source_sensor_ids),
        source_observation_ids=list(track.source_observation_ids),
        source_sensor_ids=list(track.source_sensor_ids),
        reasons=reasons,
        human_authority=human_authority,
    )


def run_synthetic_rmabm(fixture: dict[str, Any]) -> RMABMResult:
    """Run the W-RMABM G1 synthetic mission-assurance thread.

    This function intentionally stops at governed *advisory dissemination*.
    It does not generate intercept solutions, weapon cues, target designations,
    launch commands, or engagement decisions.
    """
    scenario_id = str(fixture["scenario_id"])
    now_seconds = float(fixture["scenario_time_seconds"])
    requested_action = str(fixture.get("requested_action", ALLOWED_ACTION))
    human_authority = fixture.get("human_authority")
    policy = RMABMPolicy.model_validate(fixture.get("policy", {}))
    _validate_requested_action(requested_action)

    observations = [ProvenancedObservation.model_validate(item) for item in fixture["observations"]]
    events = [MissionEvent.model_validate(item) for item in fixture.get("events", [])]
    ordered_events = replay_events(events)

    stale = sorted(
        observation.observation_id
        for observation in observations
        if now_seconds - observation.t_seconds > policy.max_observation_age_seconds
    )
    stale_set = set(stale)
    fresh = [observation for observation in observations if observation.observation_id not in stale_set]

    fusion_observations = [observation.as_fusion_observation() for observation in fresh]
    tracks = fuse_observations(
        fusion_observations,
        max_spatial_distance=float(fixture.get("max_spatial_distance", 2.0)),
        max_time_delta_seconds=float(fixture.get("max_time_delta_seconds", 3.0)),
    )

    decisions = [
        _decision_for_track(
            track=track,
            policy=policy,
            requested_action=requested_action,
            human_authority=human_authority,
        )
        for track in tracks
    ]

    provenance_complete = sum(1 for observation in observations if len(observation.source_sha256) == 64)
    provenance_completeness = provenance_complete / len(observations) if observations else 1.0

    blocked_action_requested = requested_action.strip().lower() in BLOCKED_ACTIONS
    if blocked_action_requested:
        policy_checks = [decision.decision == "BLOCK" for decision in decisions]
    else:
        policy_checks = [decision.decision in {"AUTHORIZED_ADVISORY", "HOLD"} for decision in decisions]
    policy_enforcement_rate = sum(policy_checks) / len(policy_checks) if policy_checks else 1.0

    stale_traceability = (
        sum(1 for observation_id in stale if observation_id in stale_set) / len(stale)
        if stale
        else 1.0
    )
    degraded_state_continuity = bool(stale) and bool(tracks)

    replay_material = {
        "scenario_id": scenario_id,
        "ordered_event_sequences": [event.sequence for event in ordered_events],
        "stale_observation_ids": stale,
        "fresh_observation_ids": sorted(observation.observation_id for observation in fresh),
        "decisions": [decision.model_dump(mode="json") for decision in decisions],
    }
    replay_digest = _canonical_sha256(replay_material)

    metrics = RMABMMetrics(
        provenance_completeness=provenance_completeness,
        policy_enforcement_rate=policy_enforcement_rate,
        stale_observation_traceability=stale_traceability,
        degraded_state_continuity=degraded_state_continuity,
        deterministic_replay_digest=replay_digest,
    )

    audit_material = {
        **replay_material,
        "metrics": metrics.model_dump(mode="json"),
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    audit_sha256 = _canonical_sha256(audit_material)

    return RMABMResult(
        scenario_id=scenario_id,
        evidence_state="IMPLEMENTED_IN_SOFTWARE_SYNTHETIC_ONLY",
        claims_boundary=CLAIMS_BOUNDARY,
        ordered_event_sequences=[event.sequence for event in ordered_events],
        stale_observation_ids=stale,
        fresh_observation_ids=sorted(observation.observation_id for observation in fresh),
        decisions=decisions,
        metrics=metrics,
        audit_sha256=audit_sha256,
    )
