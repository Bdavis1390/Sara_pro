from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

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


def _decision_time(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise FASARuntimeGateError("runtime admission timestamp must be timezone-aware")
    return current.astimezone(timezone.utc)


def record_verified_approval(
    store: DurableStore,
    verified: VerifiedFASAApproval,
) -> VerifiedFASAApproval:
    """Record a verified PRIME approval under the protected namespace atomically."""

    def operation(snapshot):
        patch = verified_approval_registry_patch(snapshot, verified)
        return patch, verified

    return store.transact_registry(operation)


def admit_frontier_action_transactionally(
    store: DurableStore,
    *,
    candidate: FrontierActionCandidate,
    policy: FrontierSafetyPolicy,
    target_environment: str,
    transition_id: str,
    assurance: FASAAssuranceEvidence | None = None,
    lease: FASAApprovalLease | None = None,
    verifier: PrimeSentinelFASAApprovalVerifier | None = None,
    now: datetime | None = None,
) -> FASARuntimeDecision:
    """Admit against durable capability state and consume approval before execution.

    Capability custody, approval-state validation, the admission decision, and
    approval consumption occur while one DurableStore registry transaction holds
    the store lock. An approval-gated ALLOW consumes its verified lease before the
    caller can proceed, so concurrent replay attempts cannot both receive ALLOW.

    This function only performs admission control. It does not execute an
    external operation.
    """

    if not transition_id or len(transition_id) > 128:
        raise FASARuntimeGateError("transition_id must contain 1 to 128 characters")
    if not target_environment or len(target_environment) > 128:
        raise FASARuntimeGateError(
            "target_environment must contain 1 to 128 characters"
        )

    decision_time = _decision_time(now)
    assurance = assurance or FASAAssuranceEvidence()

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
        if disposition == FrontierDisposition.ALLOW and verified is not None:
            patch = consumed_approval_registry_patch(
                snapshot,
                authorization_id=verified.authorization_id,
                transition_id=transition_id,
                consumed_at=decision_time,
            )
            approval_consumed = True

        decision = FASARuntimeDecision(
            transition_id=transition_id,
            disposition=disposition,
            reasons=tuple(reasons),
            evidence=evidence,
            approval_consumed=approval_consumed,
            authorization_id=authorization_id,
        )
        return patch, decision

    return store.transact_registry(operation)
