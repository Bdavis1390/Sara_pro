from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    UAV = "UAV"
    UGV = "UGV"
    USV = "USV"
    AMR = "AMR"
    ROBOT_ARM = "ROBOT_ARM"
    HUMANOID_SUBSYSTEM = "HUMANOID_SUBSYSTEM"
    FACTORY_CELL = "FACTORY_CELL"
    EMSKIN = "EMSKIN"


class DegradedState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    SAFE_HOLD = "SAFE_HOLD"
    RECOVERY = "RECOVERY"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class PhysicalActionDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_LIMITS = "ALLOW_WITH_LIMITS"
    DEFER = "DEFER"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    DENY = "DENY"
    SAFE_HOLD = "SAFE_HOLD"


class AssetIdentity(BaseModel):
    asset_id: str = Field(min_length=1, max_length=128)
    fleet_id: str = Field(min_length=1, max_length=128)
    asset_class: AssetClass
    hardware_revision: str = Field(min_length=1, max_length=128)
    software_revision: str = Field(min_length=1, max_length=128)
    configuration_digest: str = Field(min_length=1, max_length=256)

    @property
    def ws_uri(self) -> str:
        return f"ws://physical-ai/{self.fleet_id}/{self.asset_id}"


class PhysicalActionRequest(BaseModel):
    asset_id: str = Field(min_length=1, max_length=128)
    mission_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    action_type: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0.0, le=1.0)
    requested_authority: int = Field(default=0, ge=0)
    reversible: bool = True
    battery_soc: float = Field(default=1.0, ge=0.0, le=1.0)
    telemetry_age_s: float = Field(default=0.0, ge=0.0)
    degraded_state: DegradedState = DegradedState.NORMAL
    bounded_local_mode: bool = False
    model_digest: str | None = Field(default=None, max_length=256)
    configuration_digest: str | None = Field(default=None, max_length=256)
    observation_digest: str | None = Field(default=None, max_length=256)
    evidence_parent: str | None = Field(default=None, max_length=256)
    payload: dict[str, Any] = Field(default_factory=dict)


class PhysicalActionPolicy(BaseModel):
    policy_id: str = Field(min_length=1, max_length=128)
    allowed_action_types: list[str] = Field(default_factory=list)
    denied_action_types: list[str] = Field(default_factory=list)
    human_approval_action_types: list[str] = Field(default_factory=list)
    bounded_local_action_types: list[str] = Field(default_factory=list)
    minimum_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    minimum_battery_soc: float = Field(default=0.25, ge=0.0, le=1.0)
    maximum_telemetry_age_s: float = Field(default=2.0, ge=0.0)
    maximum_auto_authority: int = Field(default=0, ge=0)
    require_reversible: bool = True
    require_model_digest: bool = True
    require_configuration_digest: bool = True


class PhysicalActionAuthorization(BaseModel):
    action_id: str
    decision: PhysicalActionDecision
    reasons: list[str] = Field(default_factory=list)
    effective_limits: dict[str, Any] = Field(default_factory=dict)


class EvidenceManifest(BaseModel):
    mission_id: str = Field(min_length=1, max_length=128)
    asset_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    timestamp_utc: str
    action_digest: str | None = None
    policy_id: str = Field(min_length=1, max_length=128)
    decision: PhysicalActionDecision
    configuration_digest: str | None = None
    model_digest: str | None = None
    observation_digest: str | None = None
    evidence_parent: str | None = None
    result_digest: str | None = None

    @classmethod
    def from_authorization(
        cls,
        request: PhysicalActionRequest,
        policy: PhysicalActionPolicy,
        authorization: PhysicalActionAuthorization,
    ) -> "EvidenceManifest":
        return cls(
            mission_id=request.mission_id,
            asset_id=request.asset_id,
            action_id=request.action_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            policy_id=policy.policy_id,
            decision=authorization.decision,
            configuration_digest=request.configuration_digest,
            model_digest=request.model_digest,
            observation_digest=request.observation_digest,
            evidence_parent=request.evidence_parent,
        )


_ALLOWED_TRANSITIONS: dict[DegradedState, set[DegradedState]] = {
    DegradedState.NORMAL: {
        DegradedState.DEGRADED,
        DegradedState.SAFE_HOLD,
        DegradedState.EMERGENCY_STOP,
    },
    DegradedState.DEGRADED: {
        DegradedState.SAFE_HOLD,
        DegradedState.RECOVERY,
        DegradedState.EMERGENCY_STOP,
    },
    DegradedState.SAFE_HOLD: {
        DegradedState.RECOVERY,
        DegradedState.EMERGENCY_STOP,
    },
    DegradedState.RECOVERY: {
        DegradedState.NORMAL,
        DegradedState.DEGRADED,
        DegradedState.SAFE_HOLD,
        DegradedState.EMERGENCY_STOP,
    },
    DegradedState.EMERGENCY_STOP: set(),
}


def transition_allowed(current: DegradedState, target: DegradedState) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def evaluate_physical_action(
    request: PhysicalActionRequest,
    policy: PhysicalActionPolicy,
) -> PhysicalActionAuthorization:
    reasons: list[str] = []

    if request.degraded_state is DegradedState.EMERGENCY_STOP:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.DENY,
            reasons=["asset is in EMERGENCY_STOP"],
        )

    if request.action_type in policy.denied_action_types:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.DENY,
            reasons=["action type explicitly denied by policy"],
        )

    if request.action_type not in policy.allowed_action_types:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.DENY,
            reasons=["action type is not in physical-action allowlist"],
        )

    if request.action_type in policy.human_approval_action_types:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.HUMAN_APPROVAL,
            reasons=["action type requires human approval"],
        )

    if policy.require_model_digest and not request.model_digest:
        reasons.append("model digest is required")
    if policy.require_configuration_digest and not request.configuration_digest:
        reasons.append("configuration digest is required")
    if request.telemetry_age_s > policy.maximum_telemetry_age_s:
        reasons.append("telemetry is stale")
    if request.confidence < policy.minimum_confidence:
        reasons.append("confidence is below automatic-execution threshold")
    if request.requested_authority > policy.maximum_auto_authority:
        reasons.append("requested authority exceeds automatic-execution ceiling")
    if policy.require_reversible and not request.reversible:
        reasons.append("automatic execution requires reversible action")

    if reasons:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.DEFER,
            reasons=reasons,
        )

    if request.battery_soc < policy.minimum_battery_soc:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.SAFE_HOLD,
            reasons=["battery state of charge is below policy minimum"],
        )

    if request.degraded_state is DegradedState.SAFE_HOLD:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.SAFE_HOLD,
            reasons=["asset remains in SAFE_HOLD until recovery is authorized"],
        )

    if request.degraded_state is DegradedState.DEGRADED:
        if request.bounded_local_mode and request.action_type in policy.bounded_local_action_types:
            return PhysicalActionAuthorization(
                action_id=request.action_id,
                decision=PhysicalActionDecision.ALLOW_WITH_LIMITS,
                reasons=["bounded local action allowed in DEGRADED state"],
                effective_limits={"bounded_local_mode": True},
            )
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.SAFE_HOLD,
            reasons=["action is not approved for bounded local execution in DEGRADED state"],
        )

    if request.degraded_state is DegradedState.RECOVERY:
        return PhysicalActionAuthorization(
            action_id=request.action_id,
            decision=PhysicalActionDecision.ALLOW_WITH_LIMITS,
            reasons=["RECOVERY actions remain bounded until NORMAL state is restored"],
            effective_limits={"recovery_mode": True},
        )

    return PhysicalActionAuthorization(
        action_id=request.action_id,
        decision=PhysicalActionDecision.ALLOW,
        reasons=["request satisfies bounded physical-action policy gates"],
    )
