from __future__ import annotations

from typing import Any

from .sovereign_boundary_authority import VerifiedPrimeEffectAuthorization
from .sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
    assert_claimed_effect_authorization_usable,
    begin_effect_invocation_registry_patch,
    claim_effect_authorization_registry_patch,
    consumed_effect_authorization_registry_patch,
    indeterminate_effect_authorization_registry_patch,
    verified_effect_authorization_registry_patch,
)
from .sovereign_boundary_kernel import (
    SovereignBoundaryEnvelope,
    bind_prime_execution_claim,
)
from .storage import DurableStore


class PrimeEffectAuthorizationStore:
    """Durable one-time-use authority ledger backed by SARA's registry transaction.

    Claim transitions are persisted under ``DurableStore.transact_registry()``,
    so concurrent callers cannot both derive a VERIFIED -> CLAIMED transition
    from the same registry snapshot. The claim is persisted before the caller is
    handed a claim-bound envelope.

    Before any external physical executor is invoked, callers must persist the
    second one-way fence, CLAIMED -> INVOKING. This prevents two concurrent PEP
    callers from both passing a read-only CLAIMED check and invoking the same
    side effect. A stranded INVOKING record is deliberately unsafe to replay.

    The external physical side effect is intentionally not part of the file
    transaction. If execution outcome becomes uncertain after INVOKING, callers
    must move the authorization to INDETERMINATE rather than retry it.
    """

    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def register_verified(
        self, verified: VerifiedPrimeEffectAuthorization
    ) -> dict[str, Any]:
        def operation(registry: dict[str, Any]):
            patch = verified_effect_authorization_registry_patch(registry, verified)
            entry = patch[PRIME_EFFECT_AUTHZ_LEDGER_KEY][verified.authorization_id]
            return patch, dict(entry)

        return self.store.transact_registry(operation)

    def claim_and_bind(
        self,
        envelope: SovereignBoundaryEnvelope,
        *,
        authorization_id: str,
        execution_id: str,
    ) -> SovereignBoundaryEnvelope:
        def operation(registry: dict[str, Any]):
            patch = claim_effect_authorization_registry_patch(
                registry,
                authorization_id=authorization_id,
                envelope=envelope,
                execution_id=execution_id,
            )
            return patch, execution_id

        claimed_execution_id = self.store.transact_registry(operation)
        return bind_prime_execution_claim(
            envelope,
            execution_id=claimed_execution_id,
        )

    def assert_claimed(
        self,
        envelope: SovereignBoundaryEnvelope,
        *,
        authorization_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        def operation(registry: dict[str, Any]):
            entry = assert_claimed_effect_authorization_usable(
                registry,
                authorization_id=authorization_id,
                envelope=envelope,
                execution_id=execution_id,
            )
            return None, entry

        return self.store.transact_registry(operation)

    def begin_invocation(
        self,
        envelope: SovereignBoundaryEnvelope,
        *,
        authorization_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        """Persist the CLAIMED -> INVOKING fence before external actuation."""

        def operation(registry: dict[str, Any]):
            patch = begin_effect_invocation_registry_patch(
                registry,
                authorization_id=authorization_id,
                envelope=envelope,
                execution_id=execution_id,
            )
            entry = patch[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
            return patch, dict(entry)

        return self.store.transact_registry(operation)

    def consume(
        self,
        terminal_envelope: SovereignBoundaryEnvelope,
        *,
        authorization_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        def operation(registry: dict[str, Any]):
            patch = consumed_effect_authorization_registry_patch(
                registry,
                authorization_id=authorization_id,
                execution_id=execution_id,
                terminal_envelope=terminal_envelope,
            )
            entry = patch[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
            return patch, dict(entry)

        return self.store.transact_registry(operation)

    def mark_indeterminate(
        self,
        *,
        authorization_id: str,
        execution_id: str,
        reason: str,
    ) -> dict[str, Any]:
        def operation(registry: dict[str, Any]):
            patch = indeterminate_effect_authorization_registry_patch(
                registry,
                authorization_id=authorization_id,
                execution_id=execution_id,
                reason=reason,
            )
            entry = patch[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
            return patch, dict(entry)

        return self.store.transact_registry(operation)
