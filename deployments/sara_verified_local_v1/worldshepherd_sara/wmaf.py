from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .apnt_adapter import NormalizedPntSource, SyntheticPntAdapter
from .autonomy_policy import (
    AutonomousActionCandidate,
    AutonomyPolicy,
    ExecutionDisposition,
    evaluate_candidate,
)
from .qualification import canonical_digest


class WmafDisposition(str, Enum):
    OBSERVE = "OBSERVE"
    FLAG = "FLAG"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class MobilityAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)


class MobilitySource(BaseModel):
    vendor: str = Field(min_length=1)
    device: str = Field(min_length=1)
    firmware: str | None = None
    interface: str = Field(min_length=1)


class WmafEvent(BaseModel):
    schema_id: str = "WS-WMAF-EVENT-V0.1"
    event_id: str = Field(min_length=1)
    observed_utc: str = Field(min_length=1)
    asset: MobilityAsset
    source: MobilitySource
    pnt_payload: dict[str, Any]
    vehicle_state: dict[str, Any] = Field(default_factory=dict)
    autonomy_state: dict[str, Any] = Field(default_factory=dict)
    cyber_state: dict[str, Any] = Field(default_factory=dict)
    requested_action: AutonomousActionCandidate | None = None


class WmafAssessment(BaseModel):
    schema_id: str = "WS-WMAF-ASSESSMENT-V0.1"
    event_id: str
    normalized_pnt: NormalizedPntSource
    risk_flags: list[str] = Field(default_factory=list)
    action_disposition: ExecutionDisposition | None = None
    action_reasons: list[str] = Field(default_factory=list)
    disposition: WmafDisposition
    execution_performed: bool = False
    evidence_digest: str
    claims_boundary: list[str]


DEFAULT_WMAF_POLICY = AutonomyPolicy(
    policy_id="WS-WMAF-SIM-READONLY-V0.1",
    allowed_auto_action_types=["record_evidence", "raise_alert"],
    denied_action_types=[
        "vehicle_control",
        "steering",
        "braking",
        "throttle",
        "route_override",
        "actuation",
    ],
    minimum_auto_confidence=0.95,
    maximum_auto_authority=0,
    require_reversible_for_auto=True,
)


CLAIMS_BOUNDARY = [
    "Synthetic/replay mobility assurance only; no physical or field validation is claimed.",
    "No NXP, Aeva, Hyster-Yale, NVIDIA, Mobileye, Toyota, Qualcomm, or other vendor integration is implemented or validated by this module.",
    "No ASPN, pntOS, GPNTS, production vehicle bus, or proprietary automotive interface is implemented by this module.",
    "No steering, braking, throttle, route, flight, weapons, or other actuation command is executed.",
    "AUTO_ELIGIBLE is a policy-evaluation result only and must not be interpreted as execution authority or evidence that an action occurred.",
    "External, partner, laboratory, hardware, safety, cybersecurity, regulatory, and operational validation remain required.",
]


def _risk_flags(event: WmafEvent, pnt: NormalizedPntSource) -> list[str]:
    flags: list[str] = []
    health = pnt.health.strip().lower()

    if pnt.confidence < 0.75 or health not in {"nominal", "healthy", "ok"}:
        flags.append("PNT_DEGRADED")

    if bool(event.vehicle_state.get("contradictory_state", False)):
        flags.append("CONTRADICTORY_VEHICLE_STATE")

    if event.cyber_state.get("software_version_authorized") is False:
        flags.append("UNAUTHORIZED_SOFTWARE_VERSION")

    if event.vehicle_state.get("telemetry_connected") is False:
        flags.append("TELEMETRY_LOSS")
    else:
        telemetry_age = event.vehicle_state.get("telemetry_age_seconds")
        if telemetry_age is not None and float(telemetry_age) > 5.0:
            flags.append("TELEMETRY_STALE")

    return flags


def _overall_disposition(
    *,
    risk_flags: list[str],
    action_disposition: ExecutionDisposition | None,
) -> WmafDisposition:
    if action_disposition is ExecutionDisposition.DENIED:
        return WmafDisposition.DENY

    critical_flags = {
        "CONTRADICTORY_VEHICLE_STATE",
        "UNAUTHORIZED_SOFTWARE_VERSION",
    }
    if critical_flags.intersection(risk_flags):
        return WmafDisposition.ESCALATE

    if action_disposition is ExecutionDisposition.HUMAN_REVIEW_REQUIRED:
        return WmafDisposition.ESCALATE

    if risk_flags:
        return WmafDisposition.FLAG

    return WmafDisposition.OBSERVE


def assess_event(
    event: WmafEvent,
    *,
    policy: AutonomyPolicy = DEFAULT_WMAF_POLICY,
    pnt_adapter: SyntheticPntAdapter | None = None,
) -> WmafAssessment:
    """Assess one synthetic/replay mobility event without executing any action.

    WMAF-SIM v0.1 is intentionally a thin composition layer over the existing
    Worldshepherd APNT normalization and autonomy-policy primitives. It does not
    open a vehicle interface, contact a vendor system, or perform actuation.
    """

    adapter = pnt_adapter or SyntheticPntAdapter()
    normalized_pnt = adapter.normalize(event.pnt_payload)
    flags = _risk_flags(event, normalized_pnt)

    action_disposition: ExecutionDisposition | None = None
    action_reasons: list[str] = []
    if event.requested_action is not None:
        action_disposition, action_reasons = evaluate_candidate(
            event.requested_action,
            policy,
        )

    disposition = _overall_disposition(
        risk_flags=flags,
        action_disposition=action_disposition,
    )

    digest_body = {
        "schema_id": "WS-WMAF-ASSESSMENT-V0.1",
        "event": event.model_dump(mode="json"),
        "normalized_pnt": normalized_pnt.model_dump(mode="json"),
        "risk_flags": flags,
        "action_disposition": action_disposition.value if action_disposition else None,
        "action_reasons": action_reasons,
        "disposition": disposition.value,
        "execution_performed": False,
        "claims_boundary": CLAIMS_BOUNDARY,
    }

    return WmafAssessment(
        event_id=event.event_id,
        normalized_pnt=normalized_pnt,
        risk_flags=flags,
        action_disposition=action_disposition,
        action_reasons=action_reasons,
        disposition=disposition,
        execution_performed=False,
        evidence_digest=canonical_digest(digest_body),
        claims_boundary=list(CLAIMS_BOUNDARY),
    )
