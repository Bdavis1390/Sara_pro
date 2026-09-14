from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .qualification import CapabilityStatus, EvidenceScope, canonical_digest


SOVEREIGN_BOUNDARY_SCHEMA = "WS-SOVEREIGN-BOUNDARY-KERNEL-V0.1"
SOVEREIGN_BOUNDARY_EVENT_SCHEMA = "WS-SOVEREIGN-BOUNDARY-EVENT-V0.1"
SOVEREIGN_BOUNDARY_EVENT = "sovereign_boundary_transition"


class BoundaryKernelError(ValueError):
    pass


class BoundaryDomain(str, Enum):
    AI_AGENT = "AI_AGENT"
    SOFTWARE_AUTOMATION = "SOFTWARE_AUTOMATION"
    AUTONOMOUS_PLATFORM = "AUTONOMOUS_PLATFORM"
    APNT = "APNT"
    PROGRAMMABLE_BOUNDARY = "PROGRAMMABLE_BOUNDARY"
    MANUFACTURING = "MANUFACTURING"
    DIGITAL_TWIN = "DIGITAL_TWIN"
    GENERIC = "GENERIC"


class BoundaryEnvironment(str, Enum):
    SIMULATION = "SIMULATION"
    SOFTWARE_SANDBOX = "SOFTWARE_SANDBOX"
    LAB_TEST = "LAB_TEST"
    OPERATIONAL = "OPERATIONAL"
    ADMINISTRATIVE = "ADMINISTRATIVE"


class BoundaryDisposition(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    AUDIT_ONLY = "AUDIT_ONLY"


class BoundaryState(str, Enum):
    PROPOSED = "PROPOSED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class ExecutionResultStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BoundaryAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: BoundaryDomain
    action_type: str = Field(min_length=1, max_length=128)
    resource: str = Field(min_length=1, max_length=256)
    parameters: dict[str, Any] = Field(default_factory=dict)
    effect_scope: EvidenceScope
    capability_status: CapabilityStatus
    physical_validation_ref: str | None = Field(default=None, min_length=1, max_length=512)


class BoundaryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: BoundaryEnvironment
    mission_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    human_present: bool = False
    network_state: str = Field(default="UNKNOWN", min_length=1, max_length=64)


class BoundaryProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str | None = Field(default=None, max_length=256)
    agent_version: str | None = Field(default=None, max_length=128)
    schema_version: str = Field(default=SOVEREIGN_BOUNDARY_SCHEMA, min_length=1, max_length=128)
    source_evidence_refs: tuple[str, ...] = ()


class BoundaryPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: BoundaryDisposition
    policy_revision: str = Field(min_length=1, max_length=256)
    decided_by: str = Field(min_length=1, max_length=128)
    human_approval_required: bool = False
    requirements: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    decided_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def escalation_requires_human(self) -> "BoundaryPolicyDecision":
        if self.disposition == BoundaryDisposition.ESCALATE and not self.human_approval_required:
            raise ValueError("ESCALATE disposition requires human approval")
        return self


class BoundaryExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExecutionResultStatus
    outcome_ref: str = Field(min_length=1, max_length=512)
    executed_at: datetime = Field(default_factory=_utc_now)
    evidence_refs: tuple[str, ...] = ()


class SovereignBoundaryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SOVEREIGN_BOUNDARY_SCHEMA
    envelope_id: str = Field(min_length=1, max_length=128)
    actor: str = Field(min_length=1, max_length=128)
    action: BoundaryAction
    context: BoundaryContext
    provenance: BoundaryProvenance
    policy: BoundaryPolicyDecision
    state: BoundaryState
    human_approval_ref: str | None = Field(default=None, min_length=1, max_length=512)
    human_approver: str | None = Field(default=None, min_length=1, max_length=128)
    prime_authorization_ref: str | None = Field(default=None, min_length=1, max_length=128)
    prime_authorization_key_fingerprint_sha256: str | None = Field(
        default=None, min_length=64, max_length=64
    )
    action_digest: str = Field(min_length=1, max_length=128)
    execution_result: BoundaryExecutionResult | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    claims_boundary: tuple[str, ...] = (
        "Authorization does not promote capability or qualification status.",
        "SIMULATED_ONLY evidence cannot authorize non-simulation effects.",
        "Physical execution requires explicit human approval and a purpose-bound PRIME authorization reference in v0.1.",
        "Operational physical effects require PROVEN_INTERNALLY status and a physical validation reference.",
    )
    envelope_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_invariants(self) -> "SovereignBoundaryEnvelope":
        expected_action_digest = canonical_digest(self.action.model_dump(mode="json"))
        if self.action_digest != expected_action_digest:
            raise ValueError("action_digest does not match the exact action")

        if self.action.capability_status == CapabilityStatus.SIMULATED_ONLY and self.action.effect_scope != EvidenceScope.SIMULATION:
            raise ValueError("SIMULATED_ONLY capability cannot authorize a non-simulation effect")

        if self.action.effect_scope == EvidenceScope.PHYSICAL:
            if not self.policy.human_approval_required:
                raise ValueError("physical effects require explicit human approval in v0.1")
            if self.context.environment == BoundaryEnvironment.OPERATIONAL:
                if self.action.capability_status != CapabilityStatus.PROVEN_INTERNALLY:
                    raise ValueError("operational physical effects require PROVEN_INTERNALLY status")
                if not self.action.physical_validation_ref:
                    raise ValueError("operational physical effects require physical validation evidence")
            elif self.context.environment == BoundaryEnvironment.LAB_TEST:
                if self.action.capability_status not in {
                    CapabilityStatus.REQUIRES_LAB_VALIDATION,
                    CapabilityStatus.PROVEN_INTERNALLY,
                }:
                    raise ValueError("lab physical effects require lab-validation or proven status")
            else:
                raise ValueError("physical effects are allowed only in LAB_TEST or OPERATIONAL environments")

        if self.state == BoundaryState.AUTHORIZED:
            if self.policy.disposition not in {BoundaryDisposition.ALLOW, BoundaryDisposition.ESCALATE}:
                raise ValueError("AUTHORIZED state requires ALLOW or ESCALATE policy disposition")
            if self.policy.human_approval_required and not self.human_approval_ref:
                raise ValueError("AUTHORIZED state is missing required human approval")

        if self.state in {BoundaryState.EXECUTED, BoundaryState.FAILED}:
            if self.execution_result is None:
                raise ValueError("terminal execution state requires an execution result")
            if self.action.effect_scope == EvidenceScope.PHYSICAL:
                if not self.prime_authorization_ref:
                    raise ValueError("physical execution requires a PRIME authorization reference")
                if not self.prime_authorization_key_fingerprint_sha256:
                    raise ValueError("physical execution requires a PRIME signing-key fingerprint")
        if self.state not in {BoundaryState.EXECUTED, BoundaryState.FAILED} and self.execution_result is not None:
            raise ValueError("execution result is only valid in EXECUTED or FAILED state")

        if self.envelope_digest is not None:
            expected = canonical_digest(self.model_dump(mode="json", exclude={"envelope_digest"}))
            if self.envelope_digest != expected:
                raise ValueError("envelope_digest does not match the envelope")
        return self


def boundary_action_digest(action: BoundaryAction) -> str:
    return canonical_digest(action.model_dump(mode="json"))


def _seal(envelope: SovereignBoundaryEnvelope) -> SovereignBoundaryEnvelope:
    payload = envelope.model_dump(mode="json", exclude={"envelope_digest"})
    return envelope.model_copy(update={"envelope_digest": canonical_digest(payload)})


def verify_boundary_envelope(envelope: SovereignBoundaryEnvelope) -> bool:
    if envelope.action_digest != boundary_action_digest(envelope.action):
        return False
    if envelope.envelope_digest is None:
        return False
    expected = canonical_digest(envelope.model_dump(mode="json", exclude={"envelope_digest"}))
    return envelope.envelope_digest == expected


def create_boundary_envelope(
    *,
    actor: str,
    action: BoundaryAction,
    context: BoundaryContext,
    provenance: BoundaryProvenance,
    policy: BoundaryPolicyDecision,
    envelope_id: str | None = None,
) -> SovereignBoundaryEnvelope:
    if policy.disposition == BoundaryDisposition.DENY:
        state = BoundaryState.REJECTED
    elif policy.disposition in {BoundaryDisposition.ALLOW, BoundaryDisposition.ESCALATE}:
        state = (
            BoundaryState.AWAITING_HUMAN_APPROVAL
            if policy.human_approval_required
            else BoundaryState.AUTHORIZED
        )
    else:
        state = BoundaryState.PROPOSED

    envelope = SovereignBoundaryEnvelope(
        envelope_id=envelope_id or f"WS-SBK-{uuid4()}",
        actor=actor,
        action=action,
        context=context,
        provenance=provenance,
        policy=policy,
        state=state,
        action_digest=boundary_action_digest(action),
    )
    return _seal(envelope)


def authorize_after_human_approval(
    envelope: SovereignBoundaryEnvelope,
    *,
    approval_ref: str,
    approver: str,
) -> SovereignBoundaryEnvelope:
    if not verify_boundary_envelope(envelope):
        raise BoundaryKernelError("cannot authorize an unverified envelope")
    if envelope.state != BoundaryState.AWAITING_HUMAN_APPROVAL:
        raise BoundaryKernelError("envelope is not awaiting human approval")
    if envelope.policy.disposition not in {BoundaryDisposition.ALLOW, BoundaryDisposition.ESCALATE}:
        raise BoundaryKernelError("policy disposition does not permit approval")
    updated = envelope.model_copy(
        update={
            "state": BoundaryState.AUTHORIZED,
            "human_approval_ref": approval_ref,
            "human_approver": approver,
            "envelope_digest": None,
        }
    )
    validated = SovereignBoundaryEnvelope.model_validate(updated.model_dump(mode="json"))
    return _seal(validated)


def bind_prime_authorization_reference(
    envelope: SovereignBoundaryEnvelope,
    *,
    authorization_id: str,
    key_fingerprint_sha256: str,
) -> SovereignBoundaryEnvelope:
    if not verify_boundary_envelope(envelope):
        raise BoundaryKernelError("cannot bind PRIME authorization to an unverified envelope")
    if envelope.state != BoundaryState.AUTHORIZED:
        raise BoundaryKernelError("PRIME authorization may bind only to an AUTHORIZED envelope")
    if len(key_fingerprint_sha256) != 64:
        raise BoundaryKernelError("PRIME key fingerprint must be a SHA-256 hex digest")
    updated = envelope.model_copy(
        update={
            "prime_authorization_ref": authorization_id,
            "prime_authorization_key_fingerprint_sha256": key_fingerprint_sha256,
            "envelope_digest": None,
        }
    )
    validated = SovereignBoundaryEnvelope.model_validate(updated.model_dump(mode="json"))
    return _seal(validated)


def record_execution(
    envelope: SovereignBoundaryEnvelope,
    *,
    runtime_action: BoundaryAction,
    status: ExecutionResultStatus,
    outcome_ref: str,
    evidence_refs: tuple[str, ...] = (),
) -> SovereignBoundaryEnvelope:
    if not verify_boundary_envelope(envelope):
        raise BoundaryKernelError("cannot execute an unverified envelope")
    if envelope.state != BoundaryState.AUTHORIZED:
        raise BoundaryKernelError("envelope is not in AUTHORIZED state")
    runtime_digest = boundary_action_digest(runtime_action)
    if runtime_digest != envelope.action_digest:
        raise BoundaryKernelError("runtime action differs from the policy-bound action; re-evaluation required")
    if envelope.action.effect_scope == EvidenceScope.PHYSICAL:
        if not envelope.prime_authorization_ref:
            raise BoundaryKernelError("physical execution requires purpose-bound PRIME authorization")
        if not envelope.prime_authorization_key_fingerprint_sha256:
            raise BoundaryKernelError("physical execution requires PRIME key custody evidence")

    result = BoundaryExecutionResult(
        status=status,
        outcome_ref=outcome_ref,
        evidence_refs=evidence_refs,
    )
    terminal_state = BoundaryState.EXECUTED if status == ExecutionResultStatus.SUCCEEDED else BoundaryState.FAILED
    updated = envelope.model_copy(
        update={
            "state": terminal_state,
            "execution_result": result,
            "envelope_digest": None,
        }
    )
    validated = SovereignBoundaryEnvelope.model_validate(updated.model_dump(mode="json"))
    return _seal(validated)


def boundary_event_payload(envelope: SovereignBoundaryEnvelope) -> dict[str, Any]:
    if not verify_boundary_envelope(envelope):
        raise BoundaryKernelError("cannot emit evidence from an unverified envelope")
    return {
        "schema": SOVEREIGN_BOUNDARY_EVENT_SCHEMA,
        "envelope_id": envelope.envelope_id,
        "envelope_digest": envelope.envelope_digest,
        "action_digest": envelope.action_digest,
        "actor": envelope.actor,
        "domain": envelope.action.domain.value,
        "action_type": envelope.action.action_type,
        "resource": envelope.action.resource,
        "effect_scope": envelope.action.effect_scope.value,
        "capability_status": envelope.action.capability_status.value,
        "environment": envelope.context.environment.value,
        "policy_disposition": envelope.policy.disposition.value,
        "policy_revision": envelope.policy.policy_revision,
        "state": envelope.state.value,
        "human_approval_ref": envelope.human_approval_ref,
        "prime_authorization_ref": envelope.prime_authorization_ref,
        "prime_authorization_key_fingerprint_sha256": envelope.prime_authorization_key_fingerprint_sha256,
        "source_evidence_refs": list(envelope.provenance.source_evidence_refs),
        "execution_evidence_refs": (
            [] if envelope.execution_result is None else list(envelope.execution_result.evidence_refs)
        ),
        "claims_boundary": list(envelope.claims_boundary),
        "privacy_boundary": "Raw action parameters are intentionally excluded; action_digest binds the exact evaluated action.",
    }


def queue_boundary_transition(
    registry: dict[str, Any],
    envelope: SovereignBoundaryEnvelope,
) -> tuple[dict[str, Any], str]:
    from .event_outbox import queue_event_outbox_patch

    return queue_event_outbox_patch(
        registry,
        event=SOVEREIGN_BOUNDARY_EVENT,
        actor=envelope.actor,
        payload=boundary_event_payload(envelope),
    )


def build_programmable_boundary_simulation_action(
    report: Any,
    *,
    scenario_id: str,
) -> BoundaryAction:
    from .programmable_boundary_benchmark import verify_programmable_boundary_benchmark_report

    if not verify_programmable_boundary_benchmark_report(report):
        raise BoundaryKernelError("programmable-boundary report digest is invalid")
    if report.capability_status != CapabilityStatus.SIMULATED_ONLY:
        raise BoundaryKernelError("v0.1 programmable-boundary adapter requires SIMULATED_ONLY evidence")
    scenarios = {scenario.scenario_id: scenario for scenario in report.scenarios}
    scenario = scenarios.get(scenario_id)
    if scenario is None:
        raise BoundaryKernelError(f"unknown programmable-boundary scenario: {scenario_id}")

    return BoundaryAction(
        domain=BoundaryDomain.PROGRAMMABLE_BOUNDARY,
        action_type="EXECUTE_SYNTHETIC_FIELD_SHAPING_SCENARIO",
        resource=f"{report.qualification_id}:{scenario_id}",
        parameters={
            "benchmark_version": report.benchmark_version,
            "benchmark_report_digest": report.report_digest,
            "scenario_id": scenario.scenario_id,
            "mode": scenario.mode.value,
            "target_angle_degrees": scenario.target_angle_degrees,
            "preserve_angle_degrees": scenario.preserve_angle_degrees,
        },
        effect_scope=EvidenceScope.SIMULATION,
        capability_status=CapabilityStatus.SIMULATED_ONLY,
    )
