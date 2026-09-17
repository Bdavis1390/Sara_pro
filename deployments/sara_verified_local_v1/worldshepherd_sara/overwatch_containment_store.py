from __future__ import annotations

from datetime import datetime

from .overwatch_containment import (
    OverwatchContainmentDirective,
    OverwatchContainmentStatus,
    OverwatchContainmentVerifier,
    evaluate_overwatch_containment,
    verified_containment_registry_patch,
)
from .storage import DurableStore


def apply_overwatch_containment_directive(
    store: DurableStore,
    *,
    directive: OverwatchContainmentDirective,
    verifier: OverwatchContainmentVerifier,
    now: datetime | None = None,
) -> OverwatchContainmentStatus:
    """Verify and commit one OVERWATCH directive under the registry transaction lock.

    The sequence/predecessor check and the registry write operate on the same
    latest registry snapshot used by the write. On POSIX deployments with the
    MAG-1.3 process lock, concurrent containment writers and PRIME transition
    attempts therefore serialize through the same `registry.lock` boundary.

    This function intentionally does not depend on the audit/event outbox: an
    emergency HOLD must not fail merely because telemetry capacity is full.
    The signed directive remains durable evidence in the containment registry,
    and a later blocked consequential action emits its own outbox evidence.
    """

    def operation(registry):
        patch = verified_containment_registry_patch(
            registry,
            directive,
            verifier=verifier,
            now=now,
        )
        updated = dict(registry)
        updated.update(patch)
        status = evaluate_overwatch_containment(
            updated,
            prime_id=directive.prime_id,
            action=directive.action,
            target_environment=directive.target_environment,
            verifier=verifier,
            now=now,
        )
        return patch, status

    return store.transact_registry(operation)
