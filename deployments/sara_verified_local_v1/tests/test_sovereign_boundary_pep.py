from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.qualification import CapabilityStatus, EvidenceScope
from worldshepherd_sara.sovereign_boundary_authority import (
    VerifiedPrimeEffectAuthorization,
    bind_verified_prime_authorization,
)
from worldshepherd_sara.sovereign_boundary_authorization_ledger import (
    PRIME_EFFECT_AUTHZ_LEDGER_KEY,
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
    BoundaryState,
    ExecutionResultStatus,
    authorize_after_human_approval,
    create_boundary_envelope,
)
from worldshepherd_sara.sovereign_boundary_pep import (
    PhysicalEffectResult,
    SovereignBoundaryPepError,
    execute_claimed_physical_effect,
)
from worldshepherd_sara.storage import DurableStore


def _prepare_claimed(tmp_path, *, suffix: str = "001"):
    action = BoundaryAction(
        domain=BoundaryDomain.GENERIC,
        action_type="BENIGN_INTERLOCK_TEST",
        resource="lab:deenergized-authority-fixture",
        parameters={"energy_enabled": False, "channel": suffix},
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.REQUIRES_LAB_VALIDATION,
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(
            environment=BoundaryEnvironment.LAB_TEST,
            human_present=True,
            network_state="LOCAL",
        ),
        provenance=BoundaryProvenance(
            agent_version="sbk-pep-test",
            source_evidence_refs=(f"test-evidence:{suffix}",),
        ),
        policy=BoundaryPolicyDecision(
            disposition=BoundaryDisposition.ESCALATE,
            policy_revision=f"WS-SBK-PEP-TEST-{suffix}",
            decided_by="TEST_PDP",
            human_approval_required=True,
        ),
        envelope_id=f"WS-SBK-PEP-{suffix}",
    )
    envelope = authorize_after_human_approval(
        envelope,
        approval_ref=f"approval:CRE1AWS:{suffix}",
        approver="CRE1AWS",
    )
    now = datetime.now(timezone.utc)
    verified = VerifiedPrimeEffectAuthorization(
        authorization_id=f"PRIME-EFFECT-PEP-{suffix}",
        envelope_id=envelope.envelope_id,
        actor=envelope.actor,
        action_digest=envelope.action_digest,
        effect_scope=envelope.action.effect_scope,
        capability_status=envelope.action.capability_status,
        policy_revision=envelope.policy.policy_revision,
        human_approval_ref=envelope.human_approval_ref,
        key_id="prime-pep-test-key",
        key_fingerprint_sha256="b" * 64,
        nonce=f"pep-test-nonce-{suffix}-000000",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    envelope = bind_verified_prime_authorization(envelope, verified)

    store = DurableStore(tmp_path / f"sara-pep-{suffix}")
    authority = PrimeEffectAuthorizationStore(store)
    authority.register_verified(verified)
    execution_id = f"WS-SBK-PEP-EXEC-{suffix}"
    claimed = authority.claim_and_bind(
        envelope,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    return store, action, claimed, verified.authorization_id, execution_id


def test_pep_success_consumes_authority_and_queues_evidence_atomically(tmp_path):
    store, action, claimed, authorization_id, execution_id = _prepare_claimed(tmp_path)
    calls = []

    def benign_executor(runtime_action):
        calls.append(runtime_action.action_type)
        assert runtime_action.parameters["energy_enabled"] is False
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="fixture:deenergized-interlock-pass",
            evidence_refs=("sensor:none-energized",),
        )

    receipt = execute_claimed_physical_effect(
        store,
        envelope=claimed,
        runtime_action=action,
        authorization_id=authorization_id,
        execution_id=execution_id,
        executor=benign_executor,
    )

    assert calls == ["BENIGN_INTERLOCK_TEST"]
    assert receipt.terminal_envelope.state == BoundaryState.EXECUTED
    assert receipt.authorization_status == "CONSUMED"
    assert receipt.outbox_event_id.startswith("SARA-EVENT-")

    registry = store.get_registry()
    ledger = registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert ledger["status"] == "CONSUMED"
    assert ledger["terminal_envelope_digest"] == receipt.terminal_envelope.envelope_digest
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][receipt.outbox_event_id]
    assert event["status"] == "PENDING"
    assert event["payload"]["prime_execution_claim_ref"] == execution_id
    assert "parameters" not in event["payload"]

    with pytest.raises(Exception):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=benign_executor,
        )
    assert calls == ["BENIGN_INTERLOCK_TEST"]


def test_pep_action_mutation_fails_before_executor_invocation(tmp_path):
    store, action, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="002"
    )
    calls = []
    mutated = action.model_copy(
        update={"parameters": {"energy_enabled": False, "channel": "mutated"}}
    )

    def should_not_run(_runtime_action):
        calls.append("called")
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="should-not-exist",
        )

    with pytest.raises(SovereignBoundaryPepError, match="re-evaluation required"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=mutated,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=should_not_run,
        )
    assert calls == []
    registry = store.get_registry()
    assert registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]["status"] == "CLAIMED"


def test_executor_exception_moves_claim_to_indeterminate_and_blocks_retry(tmp_path):
    store, action, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="003"
    )
    calls = []

    def ambiguous_executor(_runtime_action):
        calls.append("called")
        raise OSError("simulated device transport loss after invocation")

    with pytest.raises(SovereignBoundaryPepError, match="indeterminate"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=ambiguous_executor,
        )
    assert calls == ["called"]
    registry = store.get_registry()
    entry = registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert entry["status"] == "INDETERMINATE"
    assert "executor raised after invocation" in entry["indeterminate_reason"]

    with pytest.raises(Exception):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=ambiguous_executor,
        )
    assert calls == ["called"]
