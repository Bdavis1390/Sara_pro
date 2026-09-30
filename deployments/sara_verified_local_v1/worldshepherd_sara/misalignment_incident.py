from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    CONTAINED = "CONTAINED"
    EVIDENCE_PRESERVED = "EVIDENCE_PRESERVED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    VERIFIED = "VERIFIED"
    DISCLOSED = "DISCLOSED"
    CLOSED = "CLOSED"


_ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DETECTED: {IncidentStatus.CONTAINED},
    IncidentStatus.CONTAINED: {IncidentStatus.EVIDENCE_PRESERVED},
    IncidentStatus.EVIDENCE_PRESERVED: {IncidentStatus.TRIAGED},
    IncidentStatus.TRIAGED: {IncidentStatus.INVESTIGATING},
    IncidentStatus.INVESTIGATING: {IncidentStatus.MITIGATED},
    IncidentStatus.MITIGATED: {IncidentStatus.VERIFIED},
    IncidentStatus.VERIFIED: {IncidentStatus.DISCLOSED, IncidentStatus.CLOSED},
    IncidentStatus.DISCLOSED: {IncidentStatus.CLOSED},
    IncidentStatus.CLOSED: set(),
}


class MisalignmentIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1, max_length=128)
    first_seen_at: datetime
    trajectory_id: str = Field(min_length=1, max_length=128)
    model_or_agent: str = Field(min_length=1, max_length=256)
    workflow_id: str = Field(min_length=1, max_length=128)
    human_request_hash: str = Field(min_length=1, max_length=256)
    active_policy_hash: str = Field(min_length=1, max_length=256)
    status: IncidentStatus = IncidentStatus.DETECTED
    authorization_ids: list[str] = Field(default_factory=list)
    input_evidence_refs: list[str] = Field(default_factory=list)
    actions_attempted: list[str] = Field(default_factory=list)
    actions_executed: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    external_destinations: list[str] = Field(default_factory=list)
    credential_events: list[str] = Field(default_factory=list)
    data_egress_events: list[str] = Field(default_factory=list)
    context_lineage_refs: list[str] = Field(default_factory=list)
    policy_decision_refs: list[str] = Field(default_factory=list)
    overwatch_intervention_refs: list[str] = Field(default_factory=list)
    echo_evidence_hashes: list[str] = Field(default_factory=list)
    possible_external_impact: str = "UNKNOWN"
    actual_external_impact: str = "UNKNOWN"
    root_cause_hypothesis: str = "UNDETERMINED"
    counter_hypotheses: list[str] = Field(default_factory=list)
    mitigation: str = "PENDING"
    regression_test_ids: list[str] = Field(default_factory=list)
    claim_state: str = "REQUIRES LAB VALIDATION"

    @model_validator(mode="after")
    def require_timezone_aware_timestamp(self) -> "MisalignmentIncident":
        if self.first_seen_at.tzinfo is None:
            raise ValueError("first_seen_at must be timezone-aware")
        return self


def transition_incident(
    incident: MisalignmentIncident,
    target: IncidentStatus,
) -> MisalignmentIncident:
    if target not in _ALLOWED_TRANSITIONS[incident.status]:
        raise ValueError(f"invalid incident transition: {incident.status.value} -> {target.value}")
    if target in {IncidentStatus.VERIFIED, IncidentStatus.DISCLOSED, IncidentStatus.CLOSED}:
        if not incident.echo_evidence_hashes:
            raise ValueError("incident cannot advance to verified/disclosed/closed without ECHO evidence")
        if not incident.regression_test_ids:
            raise ValueError("incident cannot advance to verified/disclosed/closed without regression tests")
    return incident.model_copy(update={"status": target}, deep=True)
