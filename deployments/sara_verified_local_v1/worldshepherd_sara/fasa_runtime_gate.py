from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .echo_event_store import EchoEventStore, EchoEventStoreError
from .event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    SINK_ECHO,
    SINK_SARA_AUDIT,
    EventOutboxError,
    deliver_event_outbox_to_echo,
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
FASA_EXECUTION_CONSUMPTION_SCHEMA = "WS-FASA-EXECUTION-READINESS-CONSUMPTION-V1"
FASA_EXECUTION_READINESS_REGISTRY_KEY = "FASA_EXECUTION_READINESS"
FASA_EXECUTION_READINESS_RECORD_SCHEMA = "WS-FASA-EXECUTION-READINESS-STATE-V1"
MAX_FASA_EXECUTION_READINESS_RECORDS = 32
_READINESS_WAITING = "WAITING_ECHO"
_READINESS_READY = "READY"
_READINESS_CONSUMED = "CONSUMED"
_VALID_READINESS_STATES = frozenset(
    {_READINESS_WAITING, _READINESS_READY, _READINESS_CONSUMED}
)


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
    external operation and is not a reusable bearer credential. Durable SARA
    readiness state must still be consumed exactly once before execution.
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
    expires_at: datetime
    ready: Literal[True] = True


class FASAExecutionReadinessConsumption(BaseModel):
    """Single-use durable consumption record immediately preceding execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[FASA_EXECUTION_CONSUMPTION_SCHEMA] = FASA_EXECUTION_CONSUMPTION_SCHEMA
    transition_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    provenance_event_id: str = Field(min_length=1, max_length=200)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_id: str = Field(min_length=1, max_length=128)
    consumed_at: datetime
    consumed: Literal[True] = True


def _decision_time(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise FASARuntimeGateError("runtime admission timestamp must be timezone-aware")
    return current.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FASARuntimeGateError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FASARuntimeGateError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise FASARuntimeGateError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _sha256_text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _readiness_record_valid(transition_id: str, entry: Any) -> bool:
    if not isinstance(transition_id, str) or not transition_id or not isinstance(entry, dict):
        return False
    if entry.get("schema") != FASA_EXECUTION_READINESS_RECORD_SCHEMA:
        return False
    if entry.get("transition_id") != transition_id:
        return False
    if entry.get("status") not in _VALID_READINESS_STATES:
        return False
    for key in ("action_id", "authorization_id", "provenance_event_id"):
        if not isinstance(entry.get(key), str) or not entry.get(key):
            return False
    if not _sha256_text(entry.get("decision_digest_sha256")):
        return False
    try:
        _parse_utc(entry.get("created_at"), label="readiness created_at")
        _parse_utc(entry.get("expires_at"), label="readiness expires_at")
    except FASARuntimeGateError:
        return False
    status = entry["status"]
    if status in {_READINESS_READY, _READINESS_CONSUMED}:
        if not _sha256_text(entry.get("echo_semantic_sha256")):
            return False
        try:
            _parse_utc(
                entry.get("echo_acknowledged_at"),
                label="readiness echo_acknowledged_at",
            )
        except FASARuntimeGateError:
            return False
    if status == _READINESS_CONSUMED:
        if not isinstance(entry.get("execution_id"), str) or not entry.get("execution_id"):
            return False
        try:
            _parse_utc(entry.get("consumed_at"), label="readiness consumed_at")
        except FASARuntimeGateError:
            return False
    return True


def _readiness_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(FASA_EXECUTION_READINESS_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise FASARuntimeGateError(
            f"{FASA_EXECUTION_READINESS_REGISTRY_KEY} must be a JSON object"
        )
    records = dict(raw)
    malformed = [
        transition_id
        for transition_id, entry in records.items()
        if not _readiness_record_valid(transition_id, entry)
    ]
    if malformed:
        raise FASARuntimeGateError("FASA execution-readiness registry is malformed")
    return records


def _waiting_readiness_registry_patch(
    registry: dict[str, Any],
    *,
    transition_id: str,
    action_id: str,
    authorization_id: str,
    provenance_event_id: str,
    decision_digest_sha256: str,
    created_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    records = _readiness_map(registry)
    if transition_id in records:
        raise FASARuntimeGateError("transition_id already has execution-readiness state")

    if len(records) >= MAX_FASA_EXECUTION_READINESS_RECORDS:
        consumed = sorted(
            (
                (key, value)
                for key, value in records.items()
                if value.get("status") == _READINESS_CONSUMED
            ),
            key=lambda item: str(item[1].get("consumed_at", "")),
        )
        while len(records) >= MAX_FASA_EXECUTION_READINESS_RECORDS and consumed:
            key, _value = consumed.pop(0)
            records.pop(key, None)
    if len(records) >= MAX_FASA_EXECUTION_READINESS_RECORDS:
        raise FASARuntimeGateError("FASA execution-readiness capacity exceeded")

    records[transition_id] = {
        "schema": FASA_EXECUTION_READINESS_RECORD_SCHEMA,
        "status": _READINESS_WAITING,
        "transition_id": transition_id,
        "action_id": action_id,
        "authorization_id": authorization_id,
        "provenance_event_id": provenance_event_id,
        "decision_digest_sha256": decision_digest_sha256,
        "created_at": _utc_iso(created_at),
        "expires_at": _utc_iso(expires_at),
    }
    return {FASA_EXECUTION_READINESS_REGISTRY_KEY: records}


def _bound_readiness_entry(
    registry: dict[str, Any],
    *,
    decision: FASARuntimeDecision,
) -> dict[str, Any]:
    if decision.evidence is None or not decision.authorization_id or not decision.provenance_event_id:
        raise FASARuntimeGateError("held decision is missing readiness binding")
    records = _readiness_map(registry)
    entry = records.get(decision.transition_id)
    if not isinstance(entry, dict):
        raise FASARuntimeGateError("durable FASA execution-readiness state is unavailable")
    expected = {
        "transition_id": decision.transition_id,
        "action_id": decision.evidence.action_id,
        "authorization_id": decision.authorization_id,
        "provenance_event_id": decision.provenance_event_id,
        "decision_digest_sha256": decision.evidence.decision_digest_sha256,
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            raise FASARuntimeGateError(f"durable readiness {key} binding mismatch")
    return entry


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
    levels at or above policy.echo_ack_before_execution_level, the same transaction
    also creates protected WAITING_ECHO execution-readiness state and the runtime
    returns ECHO_ACK_REQUIRED rather than ALLOW.

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
                working.update(outbox_patch)
                readiness_patch: dict[str, Any] = {}
                if disposition == FrontierDisposition.ECHO_ACK_REQUIRED:
                    readiness_patch = _waiting_readiness_registry_patch(
                        working,
                        transition_id=transition_id,
                        action_id=evidence.action_id,
                        authorization_id=verified.authorization_id,
                        provenance_event_id=provenance_event_id,
                        decision_digest_sha256=evidence.decision_digest_sha256,
                        created_at=decision_time,
                        expires_at=verified.expires_at,
                    )
            except (EventOutboxError, FASARuntimeGateError) as exc:
                denied_reasons = tuple(reasons) + (
                    f"required FASA provenance obligation and execution-readiness state could not be committed: {exc}",
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
            patch.update(readiness_patch)
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
    """Satisfy and verify the exact ECHO event for a held frontier transition.

    Unrelated outbox events are not drained. The exact durable readiness record,
    stable event ID, decision digest, authorization, and transition must agree.
    ECHO failures or lease/readiness expiry therefore remain fail-closed.
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

    initial_entry = _bound_readiness_entry(store.get_registry(), decision=decision)
    if initial_entry.get("status") == _READINESS_CONSUMED:
        raise FASARuntimeGateError("execution readiness has already been consumed")
    expires_at = _parse_utc(initial_entry.get("expires_at"), label="readiness expires_at")
    if acknowledged_at >= expires_at:
        raise FASARuntimeGateError("execution readiness expired before ECHO acknowledgement")

    try:
        deliver_event_outbox_to_echo(
            store,
            echo_store,
            event_id=decision.provenance_event_id,
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

    def mark_ready(snapshot):
        records = _readiness_map(snapshot)
        current = records.get(decision.transition_id)
        if not isinstance(current, dict):
            raise FASARuntimeGateError("durable execution-readiness state disappeared")
        bound = _bound_readiness_entry(snapshot, decision=decision)
        if bound.get("status") == _READINESS_CONSUMED:
            raise FASARuntimeGateError("execution readiness has already been consumed")
        durable_expiry = _parse_utc(bound.get("expires_at"), label="readiness expires_at")
        if acknowledged_at >= durable_expiry:
            raise FASARuntimeGateError("execution readiness expired before READY transition")
        if bound.get("status") == _READINESS_READY:
            if bound.get("echo_semantic_sha256") != echoed.semantic_sha256:
                raise FASARuntimeGateError("stored readiness ECHO digest mismatch")
            return None, dict(bound)
        if bound.get("status") != _READINESS_WAITING:
            raise FASARuntimeGateError("execution readiness is not waiting for ECHO")
        updated = dict(bound)
        updated.update(
            {
                "status": _READINESS_READY,
                "echo_semantic_sha256": echoed.semantic_sha256,
                "echo_acknowledged_at": _utc_iso(acknowledged_at),
            }
        )
        records[decision.transition_id] = updated
        return {FASA_EXECUTION_READINESS_REGISTRY_KEY: records}, updated

    durable_ready = store.transact_registry(mark_ready)
    durable_expiry = _parse_utc(durable_ready.get("expires_at"), label="readiness expires_at")

    return FASAEchoExecutionReadiness(
        transition_id=decision.transition_id,
        action_id=decision.evidence.action_id,
        authorization_id=decision.authorization_id,
        provenance_event_id=decision.provenance_event_id,
        decision_digest_sha256=decision.evidence.decision_digest_sha256,
        echo_semantic_sha256=echoed.semantic_sha256,
        echo_delivery_count=echoed.delivery_count,
        acknowledged_at=_parse_utc(
            durable_ready.get("echo_acknowledged_at"),
            label="readiness echo_acknowledged_at",
        ),
        expires_at=durable_expiry,
    )


def consume_execution_readiness(
    store: DurableStore,
    *,
    readiness: FASAEchoExecutionReadiness,
    execution_id: str,
    now: datetime | None = None,
) -> FASAExecutionReadinessConsumption:
    """Consume durable READY state exactly once immediately before execution.

    Replaying the same readiness receipt after a successful consumption fails
    because the protected registry state has already transitioned to CONSUMED.
    """

    consumed_at = _decision_time(now)
    if not execution_id or len(execution_id) > 128:
        raise FASARuntimeGateError("execution_id must contain 1 to 128 characters")

    def operation(snapshot):
        records = _readiness_map(snapshot)
        entry = records.get(readiness.transition_id)
        if not isinstance(entry, dict):
            raise FASARuntimeGateError("durable execution-readiness state is unavailable")
        if entry.get("status") != _READINESS_READY:
            if entry.get("status") == _READINESS_CONSUMED:
                raise FASARuntimeGateError("execution readiness has already been consumed")
            raise FASARuntimeGateError("execution readiness is not READY")
        expected = {
            "transition_id": readiness.transition_id,
            "action_id": readiness.action_id,
            "authorization_id": readiness.authorization_id,
            "provenance_event_id": readiness.provenance_event_id,
            "decision_digest_sha256": readiness.decision_digest_sha256,
            "echo_semantic_sha256": readiness.echo_semantic_sha256,
        }
        for key, value in expected.items():
            if entry.get(key) != value:
                raise FASARuntimeGateError(f"execution readiness {key} binding mismatch")
        expires_at = _parse_utc(entry.get("expires_at"), label="readiness expires_at")
        if consumed_at >= expires_at:
            raise FASARuntimeGateError("execution readiness expired before consumption")
        updated = dict(entry)
        updated.update(
            {
                "status": _READINESS_CONSUMED,
                "execution_id": execution_id,
                "consumed_at": _utc_iso(consumed_at),
            }
        )
        records[readiness.transition_id] = updated
        result = FASAExecutionReadinessConsumption(
            transition_id=readiness.transition_id,
            action_id=readiness.action_id,
            authorization_id=readiness.authorization_id,
            provenance_event_id=readiness.provenance_event_id,
            decision_digest_sha256=readiness.decision_digest_sha256,
            echo_semantic_sha256=readiness.echo_semantic_sha256,
            execution_id=execution_id,
            consumed_at=consumed_at,
        )
        return {FASA_EXECUTION_READINESS_REGISTRY_KEY: records}, result

    return store.transact_registry(operation)
