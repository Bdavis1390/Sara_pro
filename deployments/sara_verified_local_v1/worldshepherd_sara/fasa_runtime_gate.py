from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from .event_outbox import (
    SINK_ECHO,
    SINK_SARA_AUDIT,
    EventOutboxError,
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
    """Verify against the configured PRIME trust root, then record atomically.

    The caller cannot provide an alternate verifier. The FASA verifier is built
    from SARA's configured PRIME SENTINEL public-key environment, keeping the
    protected approval namespace bound to the process trust configuration.
    """

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

    For an approval-gated ALLOW, SARA commits both the VERIFIED->CONSUMED approval
    transition and an outbox event requiring SARA_AUDIT plus ECHO. If the outbox
    obligation cannot be queued, the action is denied and the approval remains
    unconsumed. Delivery to ECHO is at-least-once and occurs after this registry
    transaction; cross-store atomic delivery is not claimed.

    When an approval lease is supplied, verification uses only SARA's configured
    PRIME SENTINEL public-key trust root; the caller cannot substitute a verifier.
    This function performs admission control only and does not execute an external
    operation.
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

        disposition, reasons, verified = evaluate_frontier_action_with_approval(
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

        if disposition == FrontierDisposition.ALLOW and verified is not None:
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
            provenance_delivery = "PENDING_REQUIRED_SINKS"

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
