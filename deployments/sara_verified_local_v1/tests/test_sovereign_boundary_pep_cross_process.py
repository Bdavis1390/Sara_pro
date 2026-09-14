from __future__ import annotations

import multiprocessing
import os
from datetime import datetime, timedelta, timezone

import pytest

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
    ExecutionResultStatus,
    authorize_after_human_approval,
    create_boundary_envelope,
)
from worldshepherd_sara.sovereign_boundary_pep import (
    PhysicalEffectResult,
    execute_claimed_physical_effect,
)
from worldshepherd_sara.storage import DurableStore


def _custody() -> ExecutionCustody:
    return ExecutionCustody(
        release_index_digest="sha256:" + "1" * 64,
        release_index_file_sha256="sha256:" + "2" * 64,
        release_commit_sha="3" * 40,
        release_merge_state="PR_CANDIDATE_UNMERGED",
        release_evidence_ref="test:cross-process-release-index",
        configuration_digest="sha256:" + "4" * 64,
    )


def _prepare_cross_process_claim(data_dir):
    custody = _custody()
    action = BoundaryAction(
        domain=BoundaryDomain.GENERIC,
        action_type="BENIGN_CROSS_PROCESS_INTERLOCK_TEST",
        resource="lab:deenergized-cross-process-fixture",
        parameters={"energy_enabled": False, "purpose": "serialization-proof"},
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
            agent_version="sbk-cross-process-pep-test",
            source_evidence_refs=("test:cross-process-serialization",),
            execution_custody=custody,
        ),
        policy=BoundaryPolicyDecision(
            disposition=BoundaryDisposition.ESCALATE,
            policy_revision="WS-SBK-CROSS-PROCESS-PEP-1",
            decided_by="TEST_PDP",
            human_approval_required=True,
        ),
        envelope_id="WS-SBK-CROSS-PROCESS-PEP-001",
    )
    envelope = authorize_after_human_approval(
        envelope,
        approval_ref="approval:CRE1AWS:cross-process-001",
        approver="CRE1AWS",
    )
    now = datetime.now(timezone.utc)
    verified = VerifiedPrimeEffectAuthorization(
        authorization_id="PRIME-EFFECT-CROSS-PROCESS-001",
        envelope_id=envelope.envelope_id,
        actor=envelope.actor,
        action_digest=envelope.action_digest,
        effect_scope=envelope.action.effect_scope,
        capability_status=envelope.action.capability_status,
        policy_revision=envelope.policy.policy_revision,
        human_approval_ref=envelope.human_approval_ref,
        execution_custody=custody,
        key_id="prime-cross-process-test-key",
        key_fingerprint_sha256="c" * 64,
        nonce="cross-process-pep-nonce-000001",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    envelope = bind_verified_prime_authorization(envelope, verified)

    authority = PrimeEffectAuthorizationStore(DurableStore(data_dir))
    authority.register_verified(verified)
    execution_id = "WS-SBK-CROSS-PROCESS-EXEC-001"
    claimed = authority.claim_and_bind(
        envelope,
        authorization_id=verified.authorization_id,
        execution_id=execution_id,
    )
    return action, custody, claimed, verified.authorization_id, execution_id


def _pep_process_worker(
    label: str,
    data_dir: str,
    action,
    custody,
    claimed,
    authorization_id: str,
    execution_id: str,
    done,
    release,
    outcomes,
) -> None:
    store = DurableStore(data_dir)

    def benign_executor(_runtime_action):
        outcomes.put(("entered", label))
        if label == "A" and not release.wait(timeout=8):
            raise TimeoutError("test release timeout")
        return PhysicalEffectResult(
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref=f"fixture:cross-process:{label}",
            evidence_refs=(f"test:executor:{label}",),
        )

    try:
        receipt = execute_claimed_physical_effect(
            store,
            envelope=claimed,
            runtime_action=action,
            runtime_custody=custody,
            authorization_id=authorization_id,
            execution_id=execution_id,
            executor=benign_executor,
        )
        outcomes.put(
            (
                "success",
                label,
                receipt.authorization_status,
                receipt.execution_identity_digest,
            )
        )
    except Exception as exc:
        outcomes.put(("error", label, type(exc).__name__, str(exc)))
    finally:
        done.set()


def test_cross_process_pep_allows_only_one_executor_to_cross_invocation_fence(tmp_path):
    if os.name != "posix" or "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("cross-process PEP proof requires POSIX fork/flock")

    data_dir = tmp_path / "shared-pep-store"
    action, custody, claimed, authorization_id, execution_id = _prepare_cross_process_claim(
        data_dir
    )

    ctx = multiprocessing.get_context("fork")
    outcomes = ctx.Queue()
    release_a = ctx.Event()
    worker_a_done = ctx.Event()
    worker_b_done = ctx.Event()

    worker_a = ctx.Process(
        target=_pep_process_worker,
        args=(
            "A",
            str(data_dir),
            action,
            custody,
            claimed,
            authorization_id,
            execution_id,
            worker_a_done,
            release_a,
            outcomes,
        ),
    )
    worker_a.start()

    first = outcomes.get(timeout=5)
    assert first == ("entered", "A")

    worker_b = ctx.Process(
        target=_pep_process_worker,
        args=(
            "B",
            str(data_dir),
            action,
            custody,
            claimed,
            authorization_id,
            execution_id,
            worker_b_done,
            release_a,
            outcomes,
        ),
    )
    worker_b.start()

    second = outcomes.get(timeout=5)
    assert second[0:2] == ("error", "B"), second
    assert "invocation fence" in second[3]
    assert worker_b_done.wait(timeout=5)

    registry_during_a = DurableStore(data_dir).get_registry()
    entry = registry_during_a[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert entry["status"] == "INVOKING"
    assert entry["execution_identity_digest"] == claimed.prime_execution_identity_digest
    assert entry["execution_custody"]["configuration_digest"] == custody.configuration_digest

    release_a.set()
    third = outcomes.get(timeout=5)
    assert third[0:3] == ("success", "A", "CONSUMED")
    assert third[3] == claimed.prime_execution_identity_digest

    worker_a.join(timeout=10)
    worker_b.join(timeout=10)
    assert worker_a.exitcode == 0
    assert worker_b.exitcode == 0

    final_registry = DurableStore(data_dir).get_registry()
    final_entry = final_registry[PRIME_EFFECT_AUTHZ_LEDGER_KEY][authorization_id]
    assert final_entry["status"] == "CONSUMED"
    assert final_entry["execution_identity_digest"] == claimed.prime_execution_identity_digest
