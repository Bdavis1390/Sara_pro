from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.qualification import CapabilityStatus, EvidenceScope
from worldshepherd_sara.sovereign_boundary_authority import (
    VerifiedPrimeEffectAuthorization,
    bind_verified_prime_authorization,
)
from worldshepherd_sara.sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
    PrimeEffectAuthorizationLedgerError,
)
from worldshepherd_sara.sovereign_boundary_authority_store import (
    PrimeEffectAuthorizationStore,
)
from worldshepherd_sara.sovereign_boundary_kernel import (
    BoundaryAction,
    BoundaryContext,
    BoundaryDisposition,
    BoundaryDomain,
    BoundaryEnvironment,
    BoundaryPolicyDecision,
    BoundaryProvenance,
    ExecutionResultStatus,
    authorize_after_human_approval,
    create_boundary_envelope,
    record_execution,
)
from worldshepherd_sara.storage import DurableStore


def _authorized_lab_envelope(envelope_id: str):
    action = BoundaryAction(
        domain=BoundaryDomain.GENERIC,
        action_type="BENIGN_PHYSICAL_LAB_AUTHORITY_TEST",
        resource="lab:authority-interlock-fixture",
        parameters={"energy_enabled": False},
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.REQUIRES_LAB_VALIDATION,
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(
            environment=BoundaryEnvironment.LAB_TEST,
            human_present=True,
        ),
        provenance=BoundaryProvenance(agent_version="authority-store-test"),
        policy=BoundaryPolicyDecision(
            disposition=BoundaryDisposition.ESCALATE,
            policy_revision="WS-SBK-DURABLE-AUTH-TEST-1",
            decided_by="TEST_PDP",
            human_approval_required=True,
        ),
        envelope_id=envelope_id,
    )
    return action, authorize_after_human_approval(
        envelope,
        approval_ref=f"approval:{envelope_id}",
        approver="CRE1AWS",
    )


def _verified(envelope, authorization_id: str, nonce: str):
    now = datetime.now(timezone.utc)
    return VerifiedPrimeEffectAuthorization(
        authorization_id=authorization_id,
        envelope_id=envelope.envelope_id,
        actor=envelope.actor,
        action_digest=envelope.action_digest,
        effect_scope=envelope.action.effect_scope,
        capability_status=envelope.action.capability_status,
        policy_revision=envelope.policy.policy_revision,
        human_approval_ref=envelope.human_approval_ref,
        key_id="prime-test-key",
        key_fingerprint_sha256="a" * 64,
        nonce=nonce,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def test_claim_and_invocation_fence_are_durable_and_survive_store_reload(tmp_path):
    action, envelope = _authorized_lab_envelope("WS-SBK-DURABLE-001")
    verified = _verified(
        envelope, "PRIME-EFFECT-DURABLE-001", "durable-nonce-0000001"
    )
    envelope = bind_verified_prime_authorization(envelope, verified)

    store_path = tmp_path / "sara"
    authority = PrimeEffectAuthorizationStore(DurableStore(store_path))
    registered = authority.register_verified(verified)
    assert registered["status"] == "VERIFIED"

    execution_id = "WS-SBK-EXEC-DURABLE-001"
    claimed = authority.claim_and_bind(
        envelope,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    assert claimed.prime_execution_claim_ref == execution_id

    reloaded = PrimeEffectAuthorizationStore(DurableStore(store_path))
    entry = reloaded.assert_claimed(
        claimed,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    assert entry["status"] == "CLAIMED"

    with pytest.raises(PrimeEffectAuthorizationLedgerError, match="not claimable"):
        reloaded.claim_and_bind(
            envelope,
            authorization_id=verified.authorization_id,
            execution_id="WS-SBK-EXEC-DUPLICATE",
        )

    invoking = reloaded.begin_invocation(
        claimed,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    assert invoking["status"] == "INVOKING"
    assert "invocation_started_at" in invoking

    reloaded_again = PrimeEffectAuthorizationStore(DurableStore(store_path))
    with pytest.raises(PrimeEffectAuthorizationLedgerError, match="CLAIMED state"):
        reloaded_again.begin_invocation(
            claimed,
            authorization_id=verified.authorization_id,
            execution_id=execution_id,
        )

    completed = record_execution(
        claimed,
        runtime_action=action,
        status=ExecutionResultStatus.SUCCEEDED,
        outcome_ref="lab-record:durable-authority-store",
    )
    consumed = reloaded_again.consume(
        completed,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    assert consumed["status"] == "CONSUMED"

    final_registry = DurableStore(store_path).get_registry()
    final_entry = final_registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][
        verified.authorization_id
    ]
    assert final_entry["status"] == "CONSUMED"
    assert final_entry["terminal_envelope_digest"] == completed.envelope_digest


def test_indeterminate_claim_is_fail_closed_and_not_reusable(tmp_path):
    _action, envelope = _authorized_lab_envelope("WS-SBK-DURABLE-002")
    verified = _verified(
        envelope, "PRIME-EFFECT-DURABLE-002", "durable-nonce-0000002"
    )
    envelope = bind_verified_prime_authorization(envelope, verified)

    authority = PrimeEffectAuthorizationStore(
        DurableStore(tmp_path / "sara-indeterminate")
    )
    authority.register_verified(verified)
    authority.claim_and_bind(
        envelope,
        authorization_id=verified.authorization_id,
        execution_id="WS-SBK-EXEC-DURABLE-002",
    )
    indeterminate = authority.mark_indeterminate(
        authorization_id=verified.authorization_id,
        execution_id="WS-SBK-EXEC-DURABLE-002",
        reason="process restarted after claim; side-effect outcome cannot be proven",
    )
    assert indeterminate["status"] == "INDETERMINATE"

    with pytest.raises(PrimeEffectAuthorizationLedgerError, match="not claimable"):
        authority.claim_and_bind(
            envelope,
            authorization_id=verified.authorization_id,
            execution_id="WS-SBK-EXEC-RETRY-DENIED",
        )


def test_invoking_state_can_only_resolve_to_consumed_or_indeterminate(tmp_path):
    _action, envelope = _authorized_lab_envelope("WS-SBK-DURABLE-003")
    verified = _verified(
        envelope, "PRIME-EFFECT-DURABLE-003", "durable-nonce-0000003"
    )
    envelope = bind_verified_prime_authorization(envelope, verified)

    authority = PrimeEffectAuthorizationStore(
        DurableStore(tmp_path / "sara-invoking-indeterminate")
    )
    authority.register_verified(verified)
    claimed = authority.claim_and_bind(
        envelope,
        authorization_id=verified.authorization_id,
        execution_id="WS-SBK-EXEC-DURABLE-003",
    )
    authority.begin_invocation(
        claimed,
        authorization_id=verified.authorization_id,
        execution_id="WS-SBK-EXEC-DURABLE-003",
    )

    indeterminate = authority.mark_indeterminate(
        authorization_id=verified.authorization_id,
        execution_id="WS-SBK-EXEC-DURABLE-003",
        reason="worker disappeared after durable INVOKING fence",
    )
    assert indeterminate["status"] == "INDETERMINATE"

    with pytest.raises(PrimeEffectAuthorizationLedgerError, match="CLAIMED state"):
        authority.begin_invocation(
            claimed,
            authorization_id=verified.authorization_id,
            execution_id="WS-SBK-EXEC-DURABLE-003",
        )
