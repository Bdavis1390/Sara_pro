from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .echo_event_store import EchoEventStore, EchoEventStoreError
from .event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    MAX_PENDING_OUTBOX_EVENTS,
    SINK_ECHO,
    SINK_SARA_AUDIT,
    EventOutboxError,
    drain_event_outbox_to_echo,
    queue_event_outbox_patch,
)
from .fasa import FrontierActionCandidate, FrontierDisposition, FrontierSafetyPolicy
from .fasa_admission_evidence import FASAAdmissionEvidence, build_admission_evidence
from .fasa_approval_lease import (
    FASAAssuranceEvidence,
    FASAApprovalLease,
    PrimeSentinelFASAApprovalVerifier,
    VerifiedFASAApproval,
    consumed_approval_registry_patch,
    evaluate_frontier_action_with_approval,
    verified_approval_registry_patch,
)
from .fasa_capability_registry import (
    FASACapabilityRegistryError,
    authoritative_capability_entry,
)
from .storage import DurableStore


FASA_ECHO_EVIDENCE_SCHEMA = "WS-FASA-ECHO-EVIDENCE-V1"
FASA_ECHO_READINESS_SCHEMA = "WS-FASA-ECHO-EXECUTION-READINESS-V1"


class FASARuntimeGateError(ValueError):
    pass


class FASARuntimeDecision(BaseModel):
    """Result of one execution-authoritative FASA admission transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transition_id: str = Field(min_length=1, max_length=128)
    disposition: FrontierDisposition
    reasons: tuple[str, ...]
    evidence: FASAAdmissionEvidence | None = None
    approval_consumed: bool = False
    authorization_id: str | None = Field(default=None, min_length=1, max_length=128)
    provenance_event_id: str | None = Field(default=None, min_length=1, max_length=200)
    provenance_delivery: str = "NOT_REQUIRED"


class FASAEchoExecutionReadiness(BaseModel):
    """Evidence that a held frontier transition reached its required ECHO sink.

    This receipt establishes gate readiness only. It does not itself perform an
    external operation and is not a reusable bearer credential.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[FASA_ECHO_READINESS_SCHEMA] = FASA_ECHO_READINESS_SCHEMA
    transition_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    provenance_event_id: str = Field(min_length=1, max_length=200)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_delivery_count: int = Field(ge=1)
    acknowledged_at: datetime
    ready: Literal[True] = True


def _decision_time(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise FASARuntimeGateError("runtime admission timestamp must be timezone-aware")
    return current.astimezone(timezone.utc)


def verify_and_record_approval(
    store: DurableStore,
    *,
    lease: FASAApprovalLease,
    now: datetime | None = None,
) -> VerifiedFASAApproval:
    """Verify against the configured PRIME trust root, then record atomically."""

    verified_at = _decision_time(now)
    verifier = PrimeSentinelFASAApprovalVerifier.from_environment()
    verified = verifier.verify(lease, now=verified_at)

    def operation(snapshot):
        patch = verified_approval_registry_patch(snapshot, verified)
        return patch, verified

    return store.transact_registry(operation)


def _fasa_echo_payload(
    *,
    candidate: FrontierActionCandidate,
    policy: FrontierSafetyPolicy,
    target_environment: str,
    transition_id: str,
    evidence: FASAAdmissionEvidence,
    authorization_id: str,
) -> dict[str, object]:
    return {
        "schema": FASA_ECHO_EVIDENCE_SCHEMA,
        "transition_id": transition_id,
        "decision_digest_sha256": evidence.decision_digest_sha256,
        "disposition": evidence.disposition.value,
        "authorization_id": authorization_id,
        "evaluation_id": evidence.evaluation_id,
        "model_id": candidate.model_id,
        "model_version": candidate.model_version,
        "capability_level": int(candidate.capability_level),
        "policy_id": policy.policy_id,
        "target_environment": target_environment,
        "approval_consumed": True,
        "provenance_enabled": candidate.provenance_enabled,
        "overwatch_enabled": candidate.overwatch_enabled,
        "assessed_at": evidence.assessed_at.isoformat(),
    }


def admit_frontier_action_transactionally(
    store: DurableStore,
    *,
    candidate: FrontierActionCandidate,
    policy: FrontierSafetyPolicy,
    target_environment: str,
    transition_id: str,
    assurance: FASAAssuranceEvidence | None = None,
    lease: FASAApprovalLease | None = None,
    now: datetime | None = None,
) -> FASARuntimeDecision:
    """Admit against durable capability state and consume approval before execution.

    Capability custody, approval-state validation, the admission decision,
    approval consumption, and the durable provenance-delivery obligation occur
    while one DurableStore registry transaction holds the store lock.

    Approval-gated decisions commit a required SARA_AUDIT plus ECHO provenance
    obligation atomically with VERIFIED->CONSUMED approval state. For capability
    levels at or above policy.echo_ack_before_execution_level, the runtime returns
    ECHO_ACK_REQUIRED rather than ALLOW. A separate ECHO readiness check must then
    succeed before an external executor may treat the transition as ready.

    This function performs admission control only and does not execute an external
    operation. Cross-store atomic delivery is not claimed.
    """

    if not transition_id or len(transition_id) > 128:
        raise FASARuntimeGateError("transition_id must contain 1 to 128 characters")
    if not target_environment or len(target_environment) > 128:
        raise FASARuntimeGateError(
            "target_environment must contain 1 to 128 characters"
        )

    decision_time = _decision_time(now)
    assurance = assurance or FASAAssuranceEvidence()
    verifier = (
        PrimeSentinelFASAApprovalVerifier.from_environment()
        if lease is not None
        else None
    )

    def operation(snapshot):
        try:
            registry_entry = authoritative_capability_entry(
                snapshot,
                model_id=candidate.model_id,
                model_version=candidate.model_version,
            )
        except FASACapabilityRegistryError as exc:
            decision = FASARuntimeDecision(
                transition_id=transition_id,
                disposition=FrontierDisposition.DENIED,
                reasons=(str(exc),),
                evidence=None,
                approval_consumed=False,
                authorization_id=None,
            )
            return None, decision

        base_disposition, base_reasons, verified = evaluate_frontier_action_with_approval(
            candidate,
            registry_entry,
            policy,
            target_environment=target_environment,
            assurance=assurance,
            lease=lease,
            verifier=verifier,
            approval_registry=snapshot,
            now=decision_time,
        )

        disposition = base_disposition
        reasons = list(base_reasons)
        if (
            base_disposition == FrontierDisposition.ALLOW
            and verified is not None
            and candidate.capability_level >= policy.echo_ack_before_execution_level
        ):
            disposition = FrontierDisposition.ECHO_ACK_REQUIRED
            reasons.append(
                "synchronous ECHO acknowledgement is required before external execution"
            )

        evidence = build_admission_evidence(
            candidate,
            registry_entry,
            policy,
            disposition,
            reasons,
            verified_approval=verified,
            assessed_at=decision_time,
        )

        patch = None
        approval_consumed = False
        authorization_id = verified.authorization_id if verified else None
        provenance_event_id = None
        provenance_delivery = "NOT_REQUIRED"

        if base_disposition == FrontierDisposition.ALLOW and verified is not None:
            consumed_patch = consumed_approval_registry_patch(
                snapshot,
                authorization_id=verified.authorization_id,
                transition_id=transition_id,
                consumed_at=decision_time,
            )
            working = dict(snapshot)
            working.update(consumed_patch)
            try:
                outbox_patch, provenance_event_id = queue_event_outbox_patch(
                    working,
                    event="fasa_admission_decision",
                    actor="SARA_FASA_RUNTIME",
                    payload=_fasa_echo_payload(
                        candidate=candidate,
                        policy=policy,
                        target_environment=target_environment,
                        transition_id=transition_id,
                        evidence=evidence,
                        authorization_id=verified.authorization_id,
                    ),
                    required_sinks=(SINK_SARA_AUDIT, SINK_ECHO),
                )
            except EventOutboxError as exc:
                denied_reasons = tuple(reasons) + (
                    f"required FASA provenance obligation could not be queued: {exc}",
                )
                denied_evidence = build_admission_evidence(
                    candidate,
                    registry_entry,
                    policy,
                    FrontierDisposition.DENIED,
                    denied_reasons,
                    verified_approval=verified,
                    assessed_at=decision_time,
                )
                decision = FASARuntimeDecision(
                    transition_id=transition_id,
                    disposition=FrontierDisposition.DENIED,
                    reasons=denied_reasons,
                    evidence=denied_evidence,
                    approval_consumed=False,
                    authorization_id=verified.authorization_id,
                    provenance_event_id=None,
                    provenance_delivery="FAILED_CLOSED",
                )
                return None, decision

            patch = dict(consumed_patch)
            patch.update(outbox_patch)
            approval_consumed = True
            provenance_delivery = (
                "ECHO_ACK_REQUIRED"
                if disposition == FrontierDisposition.ECHO_ACK_REQUIRED
                else "PENDING_REQUIRED_SINKS"
            )

        decision = FASARuntimeDecision(
            transition_id=transition_id,
            disposition=disposition,
            reasons=tuple(reasons),
            evidence=evidence,
            approval_consumed=approval_consumed,
            authorization_id=authorization_id,
            provenance_event_id=provenance_event_id,
            provenance_delivery=provenance_delivery,
        )
        return patch, decision

    return store.transact_registry(operation)


def acknowledge_echo_and_confirm_execution_readiness(
    store: DurableStore,
    echo_store: EchoEventStore,
    *,
    decision: FASARuntimeDecision,
    now: datetime | None = None,
) -> FASAEchoExecutionReadiness:
    """Synchronously satisfy and verify the ECHO gate for a held F4 transition.

    No readiness receipt is returned unless the exact stable provenance event is
    present in ECHO with the decision digest and transition binding from the held
    FASA decision. ECHO failures therefore remain fail-closed.
    """

    acknowledged_at = _decision_time(now)
    if decision.disposition != FrontierDisposition.ECHO_ACK_REQUIRED:
        raise FASARuntimeGateError("decision is not waiting for ECHO acknowledgement")
    if not decision.approval_consumed:
        raise FASARuntimeGateError("held decision does not have consumed PRIME approval")
    if decision.evidence is None:
        raise FASARuntimeGateError("held decision is missing admission evidence")
    if not decision.authorization_id or not decision.provenance_event_id:
        raise FASARuntimeGateError("held decision is missing provenance binding")

    try:
        drain_event_outbox_to_echo(
            store,
            echo_store,
            limit=MAX_PENDING_OUTBOX_EVENTS,
        )
    except (EventOutboxError, EchoEventStoreError) as exc:
        raise FASARuntimeGateError(
            "required ECHO acknowledgement failed; external execution remains blocked"
        ) from exc

    registry = store.get_registry()
    outbox = registry.get(EVENT_OUTBOX_REGISTRY_KEY)
    if not isinstance(outbox, dict):
        raise FASARuntimeGateError("FASA provenance outbox is unavailable")
    entry = outbox.get(decision.provenance_event_id)
    if not isinstance(entry, dict):
        raise FASARuntimeGateError("FASA provenance event is unavailable")
    required_sinks = entry.get("required_sinks")
    delivered_sinks = entry.get("delivered_sinks")
    if not isinstance(required_sinks, list) or SINK_ECHO not in required_sinks:
        raise FASARuntimeGateError("FASA provenance event does not require ECHO")
    if not isinstance(delivered_sinks, list) or SINK_ECHO not in delivered_sinks:
        raise FASARuntimeGateError("required ECHO sink is not acknowledged")

    payload = entry.get("payload")
    if not isinstance(payload, dict):
        raise FASARuntimeGateError("FASA provenance payload is unavailable")
    if payload.get("transition_id") != decision.transition_id:
        raise FASARuntimeGateError("ECHO provenance transition binding mismatch")
    if payload.get("authorization_id") != decision.authorization_id:
        raise FASARuntimeGateError("ECHO provenance authorization binding mismatch")
    if payload.get("decision_digest_sha256") != decision.evidence.decision_digest_sha256:
        raise FASARuntimeGateError("ECHO provenance decision digest mismatch")
    if payload.get("disposition") != FrontierDisposition.ECHO_ACK_REQUIRED.value:
        raise FASARuntimeGateError("ECHO provenance disposition binding mismatch")

    try:
        echoed = echo_store.get(decision.provenance_event_id)
    except EchoEventStoreError as exc:
        raise FASARuntimeGateError("unable to verify ECHO acknowledgement") from exc
    if echoed is None:
        raise FASARuntimeGateError("required FASA event is not present in ECHO")
    echoed_payload = echoed.payload()
    if echoed_payload.get("transition_id") != decision.transition_id:
        raise FASARuntimeGateError("stored ECHO transition binding mismatch")
    if echoed_payload.get("decision_digest_sha256") != decision.evidence.decision_digest_sha256:
        raise FASARuntimeGateError("stored ECHO decision digest mismatch")

    return FASAEchoExecutionReadiness(
        transition_id=decision.transition_id,
        action_id=decision.evidence.action_id,
        authorization_id=decision.authorization_id,
        provenance_event_id=decision.provenance_event_id,
        decision_digest_sha256=decision.evidence.decision_digest_sha256,
        echo_semantic_sha256=echoed.semantic_sha256,
        echo_delivery_count=echoed.delivery_count,
        acknowledged_at=acknowledged_at,
    )
