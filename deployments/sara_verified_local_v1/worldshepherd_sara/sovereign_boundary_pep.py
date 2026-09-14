from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .event_outbox import EVENT_OUTBOX_REGISTRY_KEY, queue_event_outbox_patch
from .qualification import EvidenceScope
from .sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
    assert_claimed_effect_authorization_usable,
    consumed_effect_authorization_registry_patch,
    indeterminate_effect_authorization_registry_patch,
)
from .sovereign_boundary_kernel import (
    SOVEREIGN_BOUNDARY_EVENT,
    BoundaryAction,
    BoundaryKernelError,
    ExecutionResultStatus,
    SovereignBoundaryEnvelope,
    boundary_action_digest,
    boundary_event_payload,
    record_execution,
    verify_boundary_envelope,
)
from .storage import DurableStore


class SovereignBoundaryPepError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhysicalEffectResult:
    """Explicit executor result.

    Executors must return a result rather than relying on exceptions to signal a
    known negative outcome. An exception after invocation is treated as
    indeterminate because the PEP cannot prove whether an external side effect
    occurred before the exception was raised.
    """

    status: ExecutionResultStatus
    outcome_ref: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalEffectReceipt:
    terminal_envelope: SovereignBoundaryEnvelope
    outbox_event_id: str
    authorization_status: str


PhysicalEffectExecutor = Callable[[BoundaryAction], PhysicalEffectResult]


def _assert_preconditions(
    store: DurableStore,
    *,
    envelope: SovereignBoundaryEnvelope,
    runtime_action: BoundaryAction,
    authorization_id: str,
    execution_id: str,
) -> None:
    if not verify_boundary_envelope(envelope):
        raise SovereignBoundaryPepError("SBK envelope failed digest verification")
    if envelope.action.effect_scope != EvidenceScope.PHYSICAL:
        raise SovereignBoundaryPepError("physical-effect PEP accepts only PHYSICAL actions")
    if envelope.prime_authorization_ref != authorization_id:
        raise SovereignBoundaryPepError("PRIME authorization reference mismatch")
    if envelope.prime_execution_claim_ref != execution_id:
        raise SovereignBoundaryPepError("PRIME execution claim reference mismatch")
    if boundary_action_digest(runtime_action) != envelope.action_digest:
        raise SovereignBoundaryPepError(
            "runtime action differs from the policy-bound action; re-evaluation required"
        )

    registry = store.get_registry()
    assert_claimed_effect_authorization_usable(
        registry,
        authorization_id=authorization_id,
        envelope=envelope,
        execution_id=execution_id,
    )


def _mark_indeterminate_best_effort(
    store: DurableStore,
    *,
    authorization_id: str,
    execution_id: str,
    reason: str,
) -> None:
    try:
        def operation(registry: dict[str, Any]):
            patch = indeterminate_effect_authorization_registry_patch(
                registry,
                authorization_id=authorization_id,
                execution_id=execution_id,
                reason=reason,
            )
            return patch, None

        store.transact_registry(operation)
    except Exception:
        # The original failure is more important. If durable state cannot be
        # updated, operators must treat the claim as unresolved/unsafe to retry.
        pass


def _consume_and_queue_atomically(
    store: DurableStore,
    *,
    authorization_id: str,
    execution_id: str,
    terminal_envelope: SovereignBoundaryEnvelope,
) -> tuple[str, str]:
    """Persist CONSUMED authority and a pending ECHO event in one registry write."""

    def operation(registry: dict[str, Any]):
        consumed_patch = consumed_effect_authorization_registry_patch(
            registry,
            authorization_id=authorization_id,
            execution_id=execution_id,
            terminal_envelope=terminal_envelope,
        )
        working = dict(registry)
        working.update(consumed_patch)
        event_patch, event_id = queue_event_outbox_patch(
            working,
            event=SOVEREIGN_BOUNDARY_EVENT,
            actor=terminal_envelope.actor,
            payload=boundary_event_payload(terminal_envelope),
        )
        combined = dict(consumed_patch)
        combined.update(event_patch)
        entry = consumed_patch[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
        return combined, (event_id, str(entry["status"]))

    return store.transact_registry(operation)


def execute_claimed_physical_effect(
    store: DurableStore,
    *,
    envelope: SovereignBoundaryEnvelope,
    runtime_action: BoundaryAction,
    authorization_id: str,
    execution_id: str,
    executor: PhysicalEffectExecutor,
) -> PhysicalEffectReceipt:
    """Run one already-claimed physical effect through the Worldshepherd PEP.

    Safety/authority sequence:

    1. Verify sealed SBK envelope and exact runtime action.
    2. Re-read durable PRIME ledger and require matching CLAIMED state.
    3. Invoke exactly one executor callback.
    4. Convert the explicit executor result into a terminal SBK envelope.
    5. Atomically persist PRIME CLAIMED->CONSUMED plus the pending SARA/ECHO
       outbox event in one DurableStore registry transaction.

    If the executor raises, the claim is moved to INDETERMINATE best-effort and
    is never automatically retried. If durable finalization fails after the
    executor returns, the claim is likewise marked INDETERMINATE best-effort.

    This does not make an external physical side effect transactionally atomic
    with local storage. It intentionally converts uncertainty into a fail-closed
    human-review state instead of pretending exactly-once actuation is possible.
    """

    _assert_preconditions(
        store,
        envelope=envelope,
        runtime_action=runtime_action,
        authorization_id=authorization_id,
        execution_id=execution_id,
    )

    try:
        result = executor(runtime_action)
    except Exception as exc:
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason=f"executor raised after invocation: {type(exc).__name__}",
        )
        raise SovereignBoundaryPepError(
            "executor outcome is indeterminate; authorization is unsafe to retry"
        ) from exc

    if not isinstance(result, PhysicalEffectResult):
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason="executor returned an invalid result object after invocation",
        )
        raise SovereignBoundaryPepError(
            "executor returned invalid result; authorization is unsafe to retry"
        )
    if not result.outcome_ref:
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason="executor returned an empty outcome reference after invocation",
        )
        raise SovereignBoundaryPepError(
            "executor omitted outcome evidence; authorization is unsafe to retry"
        )

    try:
        terminal = record_execution(
            envelope,
            runtime_action=runtime_action,
            status=result.status,
            outcome_ref=result.outcome_ref,
            evidence_refs=result.evidence_refs,
        )
        event_id, authorization_status = _consume_and_queue_atomically(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            terminal_envelope=terminal,
        )
    except Exception as exc:
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason=f"post-execution durable finalization failed: {type(exc).__name__}",
        )
        raise SovereignBoundaryPepError(
            "physical-effect result could not be durably finalized; human reconciliation required"
        ) from exc

    return PhysicalEffectReceipt(
        terminal_envelope=terminal,
        outbox_event_id=event_id,
        authorization_status=authorization_status,
    )
