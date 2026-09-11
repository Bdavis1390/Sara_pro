from __future__ import annotations

from enum import Enum, IntEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CapabilityLevel(IntEnum):
    """Worldshepherd Frontier AI Safety Assurance capability ladder."""

    F0 = 0  # text/reasoning only
    F1 = 1  # read-only tools/data
    F2 = 2  # bounded reversible tool actions
    F3 = 3  # consequential external actions
    F4 = 4  # persistent/multi-agent or high-risk frontier capability
    F5 = 5  # plausibly catastrophic or material loss-of-control capability


class FrontierDisposition(str, Enum):
    ALLOW = "ALLOW"
    ECHO_ACK_REQUIRED = "ECHO_ACK_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENIED = "DENIED"


class CapabilityRegistryEntry(BaseModel):
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    assessed_level: CapabilityLevel
    maximum_authorized_level: CapabilityLevel
    evaluation_id: str = Field(min_length=1)
    evaluation_current: bool = True

    @model_validator(mode="after")
    def validate_authorization_ceiling(self) -> "CapabilityRegistryEntry":
        if self.maximum_authorized_level > self.assessed_level:
            raise ValueError(
                "maximum_authorized_level cannot exceed assessed_level"
            )
        return self


class FrontierActionCandidate(BaseModel):
    action_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    capability_level: CapabilityLevel
    reversible: bool
    consequential_external_effect: bool = False
    human_approval_present: bool = False
    safety_case_current: bool = False
    independent_review_current: bool = False
    provenance_enabled: bool = True
    overwatch_enabled: bool = True
    self_authorization_attempt: bool = False
    governing_policy_modification_attempt: bool = False
    monitoring_suppression_attempt: bool = False
    unbounded_agent_creation_attempt: bool = False
    metadata: dict = Field(default_factory=dict)


class FrontierSafetyPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    maximum_automatic_level: CapabilityLevel = CapabilityLevel.F2
    human_review_level: CapabilityLevel = CapabilityLevel.F3
    safety_case_level: CapabilityLevel = CapabilityLevel.F4
    independent_review_level: CapabilityLevel = CapabilityLevel.F4
    echo_ack_before_execution_level: CapabilityLevel = CapabilityLevel.F4
    require_human_for_irreversible: bool = True
    require_human_for_consequential_external_effect: bool = True
    require_provenance: bool = True
    require_overwatch: bool = True
    deny_self_authorization: bool = True
    deny_governing_policy_modification: bool = True
    deny_monitoring_suppression: bool = True
    deny_unbounded_agent_creation: bool = True
    # WS-FASA v1 has no policy switch that can authorize F5. Keeping this
    # serialized field pinned to False makes attempts to enable it fail model
    # validation rather than silently changing the execution boundary.
    allow_f5_when_all_gates_pass: Literal[False] = False

    @model_validator(mode="after")
    def validate_echo_ack_threshold(self) -> "FrontierSafetyPolicy":
        if self.echo_ack_before_execution_level < self.human_review_level:
            raise ValueError(
                "echo_ack_before_execution_level cannot be below human_review_level"
            )
        if self.echo_ack_before_execution_level > CapabilityLevel.F4:
            raise ValueError(
                "echo_ack_before_execution_level cannot exceed F4 while F5 is disabled"
            )
        return self


def evaluate_frontier_action(
    candidate: FrontierActionCandidate,
    registry: CapabilityRegistryEntry,
    policy: FrontierSafetyPolicy,
) -> tuple[FrontierDisposition, list[str]]:
    """Fail closed unless identity, evidence, authority, and safety gates are satisfied."""

    denied: list[str] = []
    review: list[str] = []

    if candidate.model_id != registry.model_id or candidate.model_version != registry.model_version:
        denied.append("candidate identity/version does not match capability registry entry")

    if not registry.evaluation_current:
        denied.append("capability evaluation is not current")

    if candidate.capability_level > registry.assessed_level:
        denied.append("requested capability exceeds assessed capability level")

    if candidate.capability_level > registry.maximum_authorized_level:
        denied.append("requested capability exceeds maximum authorized registry level")

    if policy.require_provenance and not candidate.provenance_enabled:
        denied.append("required ECHO provenance path is not enabled")

    if policy.require_overwatch and not candidate.overwatch_enabled:
        denied.append("required independent OVERWATCH monitor is not enabled")

    if policy.deny_self_authorization and candidate.self_authorization_attempt:
        denied.append("self-authorization is prohibited")

    if policy.deny_governing_policy_modification and candidate.governing_policy_modification_attempt:
        denied.append("AI-directed modification of governing safety policy is prohibited")

    if policy.deny_monitoring_suppression and candidate.monitoring_suppression_attempt:
        denied.append("monitoring suppression is prohibited")

    if policy.deny_unbounded_agent_creation and candidate.unbounded_agent_creation_attempt:
        denied.append("unbounded agent creation is prohibited")

    if candidate.capability_level >= policy.safety_case_level and not candidate.safety_case_current:
        denied.append("current safety case is required at this capability level")

    if (
        candidate.capability_level >= policy.independent_review_level
        and not candidate.independent_review_current
    ):
        denied.append("current independent review is required at this capability level")

    if candidate.capability_level == CapabilityLevel.F5:
        denied.append("F5 execution is disabled by WS-FASA v1 invariant")

    if denied:
        return FrontierDisposition.DENIED, denied

    if candidate.capability_level >= policy.human_review_level and not candidate.human_approval_present:
        review.append("human approval is required at this capability level")

    if (
        policy.require_human_for_irreversible
        and not candidate.reversible
        and not candidate.human_approval_present
    ):
        review.append("irreversible action requires human approval")

    if (
        policy.require_human_for_consequential_external_effect
        and candidate.consequential_external_effect
        and not candidate.human_approval_present
    ):
        review.append("consequential external effect requires human approval")

    if candidate.capability_level > policy.maximum_automatic_level and not candidate.human_approval_present:
        review.append("requested capability exceeds automatic-execution ceiling")

    if review:
        return FrontierDisposition.HUMAN_REVIEW_REQUIRED, review

    return FrontierDisposition.ALLOW, [
        "identity, evaluation, authorization, provenance, monitoring, and applicable review gates satisfied"
    ]
