from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .event_outbox import queue_event_outbox_patch
from .qualification import EvidenceScope
from .sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
    begin_effect_invocation_registry_patch,
    consumed_effect_authorization_registry_patch,
    indeterminate_effect_authorization_registry_patch,
)
from .sovereign_boundary_custody import ExecutionCustody, execution_custody_matches
from .sovereign_boundary_kernel import (
    SOVEREIGN_BOUNDARY_EVENT,
    BoundaryAction,
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
    execution_identity_digest: str


PhysicalEffectExecutor = Callable[[BoundaryAction], PhysicalEffectResult]


def _assert_local_preconditions(
    *,
    envelope: SovereignBoundaryEnvelope,
    runtime_action: BoundaryAction,
    runtime_custody: ExecutionCustody,
    authorization_id: str,
    execution_id: str,
) -> None:
    if not verify_boundary_envelope(envelope):
        raise SovereignBoundaryPepError("SBK envelope failed digest verification")
    if envelope.action.effect_scope != EvidenceScope.PHYSICAL:
        raise SovereignBoundaryPepError(
            "physical-effect PEP accepts only PHYSICAL actions"
        )
    if envelope.prime_authorization_ref != authorization_id:
        raise SovereignBoundaryPepError("PRIME authorization reference mismatch")
    if envelope.prime_execution_claim_ref != execution_id:
        raise SovereignBoundaryPepError("PRIME execution claim reference mismatch")
    if not envelope.prime_execution_identity_digest:
        raise SovereignBoundaryPepError("custody-bound execution identity is missing")
    if boundary_action_digest(runtime_action) != envelope.action_digest:
        raise SovereignBoundaryPepError(
            "runtime action differs from the policy-bound action; re-evaluation required"
        )
    expected_custody = envelope.provenance.execution_custody
    if expected_custody is None:
        raise SovereignBoundaryPepError(
            "physical-effect envelope is missing release/configuration custody"
        )
    if not execution_custody_matches(expected_custody, runtime_custody):
        raise SovereignBoundaryPepError(
            "runtime release/configuration custody differs from authorized custody; re-authorization required"
        )


def _begin_invocation_fence(
    store: DurableStore,
    *,
    envelope: SovereignBoundaryEnvelope,
    authorization_id: str,
    execution_id: str,
) -> None:
    """Atomically move CLAIMED -> INVOKING before the executor can run."""

    def operation(registry: dict[str, Any]):
        patch = begin_effect_invocation_registry_patch(
            registry,
            authorization_id=authorization_id,
            envelope=envelope,
            execution_id=execution_id,
        )
        return patch, None

    try:
        store.transact_registry(operation)
    except Exception as exc:
        raise SovereignBoundaryPepError(
            "physical-effect invocation fence could not be acquired"
        ) from exc


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
        pass


def _consume_and_queue_atomically(
    store: DurableStore,
    *,
    authorization_id: str,
    execution_id: str,
    terminal_envelope: SovereignBoundaryEnvelope,
) -> tuple[str, str]:
    """Persist INVOKING->CONSUMED plus a pending ECHO event in one registry write."""

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
    runtime_custody: ExecutionCustody,
    authorization_id: str,
    execution_id: str,
    executor: PhysicalEffectExecutor,
) -> PhysicalEffectReceipt:
    """Run one claimed physical effect through the Worldshepherd PEP.

    The PEP now rechecks two independently mutable identities immediately before
    the one-way invocation fence:

    * exact action identity; and
    * exact release/configuration execution custody.

    A policy-approved action therefore cannot be executed by a different
    declared software release or configuration without fresh authorization.
    The check binds evidence identity supplied by the compliant runtime; it does
    not independently attest process memory or prevent a malicious program from
    bypassing the PEP.
    """

    _assert_local_preconditions(
        envelope=envelope,
        runtime_action=runtime_action,
        runtime_custody=runtime_custody,
        authorization_id=authorization_id,
        execution_id=execution_id,
    )
    _begin_invocation_fence(
        store,
        envelope=envelope,
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
            reason=f"executor raised after INVOKING fence: {type(exc).__name__}",
        )
        raise SovereignBoundaryPepError(
            "executor outcome is indeterminate; authorization is unsafe to retry"
        ) from exc

    if not isinstance(result, PhysicalEffectResult):
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason="executor returned an invalid result object after INVOKING fence",
        )
        raise SovereignBoundaryPepError(
            "executor returned invalid result; authorization is unsafe to retry"
        )
    if not result.outcome_ref:
        _mark_indeterminate_best_effort(
            store,
            authorization_id=authorization_id,
            execution_id=execution_id,
            reason="executor returned an empty outcome reference after INVOKING fence",
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

    assert terminal.prime_execution_identity_digest is not None
    return PhysicalEffectReceipt(
        terminal_envelope=terminal,
        outbox_event_id=event_id,
        authorization_status=authorization_status,
        execution_identity_digest=terminal.prime_execution_identity_digest,
    )
