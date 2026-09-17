from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event, Thread

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
from worldshepherd_sara.sovereign_boundary_custody import ExecutionCustody
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


def _custody(*, release_hex: str = "1", config_hex: str = "4") -> ExecutionCustody:
    return ExecutionCustody(
        release_index_digest="sha256:" + release_hex * 64,
        release_index_file_sha256="sha256:" + "2" * 64,
        release_commit_sha="3" * 40,
        release_merge_state="PR_CANDIDATE_UNMERGED",
        release_evidence_ref="test:pep-release-index",
        configuration_digest="sha256:" + config_hex * 64,
    )


def _prepare_claimed(tmp_path, *, suffix: str = "001"):
    custody = _custody()
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
            execution_custody=custody,
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
        execution_custody=custody,
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
    return store, action, custody, claimed, verified.authorization_id, execution_id


def test_pep_success_consumes_authority_and_queues_evidence_atomically(tmp_path):
    store, action, custody, claimed, authorization_id, execution_id = _prepare_claimed(tmp_path)
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
        runtime_custody=custody,
        authorization_id=authorization_id,
        execution_id=execution_id,
        executor=benign_executor,
    )

    assert calls == ["BENIGN_INTERLOCK_TEST"]
    assert receipt.terminal_envelope.state == BoundaryState.EXECUTED
    assert receipt.authorization_status == "CONSUMED"
    assert receipt.outbox_event_id.startswith("SARA-EVENT-")
    assert receipt.execution_identity_digest == claimed.prime_execution_identity_digest

    registry = store.get_registry()
    ledger = registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert ledger["status"] == "CONSUMED"
    assert "invocation_started_at" in ledger
    assert ledger["execution_identity_digest"] == receipt.execution_identity_digest
    assert ledger["terminal_envelope_digest"] == receipt.terminal_envelope.envelope_digest
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][receipt.outbox_event_id]
    assert event["status"] == "PENDING"
    assert event["payload"]["prime_execution_claim_ref"] == execution_id
    assert event["payload"]["prime_execution_identity_digest"] == receipt.execution_identity_digest
    assert event["payload"]["configuration_digest"] == custody.configuration_digest
    assert "parameters" not in event["payload"]

    with pytest.raises(SovereignBoundaryPepError, match="fence"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=benign_executor,
        )
    assert calls == ["BENIGN_INTERLOCK_TEST"]


def test_pep_action_mutation_fails_before_executor_invocation(tmp_path):
    store, action, custody, claimed, authorization_id, execution_id = _prepare_claimed(
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
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=should_not_run,
        )
    assert calls == []
    assert store.get_registry()[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]["status"] == "CLAIMED"


def test_pep_configuration_drift_fails_before_invocation_fence(tmp_path):
    store, action, _custody_bound, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="006"
    )
    calls = []
    drifted = _custody(config_hex="5")

    def should_not_run(_runtime_action):
        calls.append("called")
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="should-not-exist",
        )

    with pytest.raises(SovereignBoundaryPepError, match="custody differs"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=drifted,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=should_not_run,
        )
    assert calls == []
    assert store.get_registry()[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]["status"] == "CLAIMED"


def test_pep_release_drift_fails_before_invocation_fence(tmp_path):
    store, action, _custody_bound, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="007"
    )
    calls = []
    drifted = _custody(release_hex="6")

    def should_not_run(_runtime_action):
        calls.append("called")
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="should-not-exist",
        )

    with pytest.raises(SovereignBoundaryPepError, match="custody differs"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=drifted,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=should_not_run,
        )
    assert calls == []
    assert store.get_registry()[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]["status"] == "CLAIMED"


def test_executor_exception_moves_invoking_to_indeterminate_and_blocks_retry(tmp_path):
    store, action, custody, claimed, authorization_id, execution_id = _prepare_claimed(
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
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=ambiguous_executor,
        )
    assert calls == ["called"]
    registry = store.get_registry()
    entry = registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert entry["status"] == "INDETERMINATE"
    assert "executor raised after INVOKING fence" in entry["indeterminate_reason"]
    assert "invocation_started_at" in entry

    with pytest.raises(SovereignBoundaryPepError, match="fence"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=ambiguous_executor,
        )
    assert calls == ["called"]


def test_concurrent_pep_callers_cannot_both_cross_invocation_fence(tmp_path):
    store, action, custody, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="004"
    )
    entered_executor = Event()
    release_executor = Event()
    calls = []
    first_receipts = []
    first_errors = []

    def slow_executor(_runtime_action):
        calls.append("called")
        entered_executor.set()
        assert release_executor.wait(timeout=5), "test did not release executor"
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="fixture:concurrency-fence-pass",
        )

    def first_caller():
        try:
            first_receipts.append(
                execute_claimed_physical_effect(
                    store,
                    envelope=claimed,
                    runtime_action=action,
                    runtime_custody=custody,
                    authorization_id=authorization_id,
                    execution_id=execution_id,
                    executor=slow_executor,
                )
            )
        except Exception as exc:  # pragma: no cover - diagnostic capture
            first_errors.append(exc)

    worker = Thread(target=first_caller, daemon=True)
    worker.start()
    assert entered_executor.wait(timeout=5), "first caller never reached executor"

    registry_while_first_is_running = store.get_registry()
    assert registry_while_first_is_running[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]["status"] == "INVOKING"

    with pytest.raises(SovereignBoundaryPepError, match="fence"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=slow_executor,
        )

    assert calls == ["called"]
    release_executor.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert first_errors == []
    assert len(first_receipts) == 1
    assert first_receipts[0].authorization_status == "CONSUMED"
    assert calls == ["called"]


def test_authorization_expiry_is_rechecked_at_invocation_boundary(tmp_path):
    store, action, custody, claimed, authorization_id, execution_id = _prepare_claimed(
        tmp_path, suffix="005"
    )
    calls = []

    registry = store.get_registry()
    ledger = dict(registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY])
    expired = dict(ledger[authorization_id])
    expired["expires_at"] = "2000-01-01T00:00:00Z"
    ledger[authorization_id] = expired
    store.patch_registry({PRIME_EFFECT_AUTHZ_LEDGER_KEY: ledger})

    def should_not_run(_runtime_action):
        calls.append("called")
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="should-not-exist",
        )

    with pytest.raises(SovereignBoundaryPepError, match="fence"):
        execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=should_not_run,
        )

    assert calls == []
    final = store.get_registry()[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert final["status"] == "CLAIMED"
