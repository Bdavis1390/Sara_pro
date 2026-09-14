from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.programmable_boundary_benchmark import run_programmable_boundary_benchmark
from worldshepherd_sara.qualification import CapabilityStatus, EvidenceScope
from worldshepherd_sara.sovereign_boundary_custody import ExecutionCustody
from worldshepherd_sara.sovereign_boundary_kernel import (
    BoundaryAction,
    BoundaryContext,
    BoundaryDisposition,
    BoundaryDomain,
    BoundaryEnvironment,
    BoundaryKernelError,
    BoundaryPolicyDecision,
    BoundaryProvenance,
    BoundaryState,
    ExecutionResultStatus,
    authorize_after_human_approval,
    boundary_event_payload,
    build_programmable_boundary_simulation_action,
    create_boundary_envelope,
    queue_boundary_transition,
    record_execution,
    verify_boundary_envelope,
)


def _custody(suffix: str = "1") -> ExecutionCustody:
    marker = (suffix * 64)[:64]
    return ExecutionCustody(
        release_index_digest="sha256:" + marker,
        release_index_file_sha256="sha256:" + "a" * 64,
        release_commit_sha="b" * 40,
        release_merge_state="PR_CANDIDATE_UNMERGED",
        release_evidence_ref=f"test:release-index:{suffix}",
        configuration_digest="sha256:" + "c" * 64,
    )


def _software_action(**updates):
    values = {
        "domain": BoundaryDomain.AI_AGENT,
        "action_type": "CALL_TOOL",
        "resource": "demo-tool",
        "parameters": {"query": "bounded-test"},
        "effect_scope": EvidenceScope.SOFTWARE,
        "capability_status": CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
    }
    values.update(updates)
    return BoundaryAction(**values)


def _policy(**updates):
    values = {
        "disposition": BoundaryDisposition.ALLOW,
        "policy_revision": "WS-SBK-TEST-POLICY-1",
        "decided_by": "TEST_PDP",
    }
    values.update(updates)
    return BoundaryPolicyDecision(**values)


def _context(**updates):
    values = {
        "environment": BoundaryEnvironment.SOFTWARE_SANDBOX,
        "mission_id": "MISSION-TEST-001",
        "network_state": "CONNECTED",
    }
    values.update(updates)
    return BoundaryContext(**values)


def _provenance(**updates):
    values = {
        "agent_version": "test-agent-1",
        "source_evidence_refs": ("evidence:test:1",),
    }
    values.update(updates)
    return BoundaryProvenance(**values)


def test_software_action_is_hash_bound_authorized_and_recordable():
    action = _software_action()
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=_context(),
        provenance=_provenance(),
        policy=_policy(),
        envelope_id="WS-SBK-TEST-001",
    )
    assert envelope.state == BoundaryState.AUTHORIZED
    assert verify_boundary_envelope(envelope) is True

    completed = record_execution(
        envelope,
        runtime_action=action,
        status=ExecutionResultStatus.SUCCEEDED,
        outcome_ref="result:test:1",
        evidence_refs=("echo:test:1",),
    )
    assert completed.state == BoundaryState.EXECUTED
    assert completed.execution_result is not None
    assert completed.execution_result.status == ExecutionResultStatus.SUCCEEDED
    assert verify_boundary_envelope(completed) is True


def test_runtime_action_mutation_requires_policy_reevaluation():
    action = _software_action(parameters={"query": "original"})
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=_context(),
        provenance=_provenance(),
        policy=_policy(),
    )
    mutated = _software_action(parameters={"query": "changed-after-policy"})

    with pytest.raises(BoundaryKernelError, match="re-evaluation required"):
        record_execution(
            envelope,
            runtime_action=mutated,
            status=ExecutionResultStatus.SUCCEEDED,
            outcome_ref="result:should-not-exist",
        )


def test_simulated_only_maturity_cannot_be_laundered_into_physical_effect():
    action = _software_action(
        domain=BoundaryDomain.PROGRAMMABLE_BOUNDARY,
        action_type="PHYSICAL_FIELD_COMMAND",
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.SIMULATED_ONLY,
    )

    with pytest.raises(ValidationError, match="SIMULATED_ONLY"):
        create_boundary_envelope(
            actor="SSPADAWANZZ",
            action=action,
            context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
            provenance=_provenance(execution_custody=_custody()),
            policy=_policy(human_approval_required=True),
        )


def test_physical_effect_without_release_configuration_custody_fails_closed():
    action = _software_action(
        domain=BoundaryDomain.GENERIC,
        action_type="LAB_AUTHORITY_TEST",
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.REQUIRES_LAB_VALIDATION,
    )
    with pytest.raises(ValidationError, match="execution custody"):
        create_boundary_envelope(
            actor="SSPADAWANZZ",
            action=action,
            context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
            provenance=_provenance(),
            policy=_policy(human_approval_required=True),
        )


def test_operational_physical_effect_requires_proven_validation_and_human_approval():
    action = _software_action(
        domain=BoundaryDomain.AUTONOMOUS_PLATFORM,
        action_type="AUTHORIZED_PHYSICAL_TEST_ACTION",
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        physical_validation_ref="WS-QE-PHYSICAL-VALIDATION-001",
    )

    with pytest.raises(ValidationError, match="human approval"):
        create_boundary_envelope(
            actor="SSPADAWANZZ",
            action=action,
            context=BoundaryContext(environment=BoundaryEnvironment.OPERATIONAL),
            provenance=_provenance(execution_custody=_custody()),
            policy=_policy(human_approval_required=False),
        )

    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(
            environment=BoundaryEnvironment.OPERATIONAL,
            human_present=True,
        ),
        provenance=_provenance(execution_custody=_custody()),
        policy=_policy(human_approval_required=True),
    )
    assert envelope.state == BoundaryState.AWAITING_HUMAN_APPROVAL

    approved = authorize_after_human_approval(
        envelope,
        approval_ref="approval:human:001",
        approver="CRE1AWS",
    )
    assert approved.state == BoundaryState.AUTHORIZED
    assert approved.human_approver == "CRE1AWS"
    assert verify_boundary_envelope(approved) is True


def test_lab_validation_action_stays_human_gated_without_claim_promotion():
    action = _software_action(
        domain=BoundaryDomain.PROGRAMMABLE_BOUNDARY,
        action_type="LAB_VALIDATION_EXPERIMENT",
        effect_scope=EvidenceScope.PHYSICAL,
        capability_status=CapabilityStatus.REQUIRES_LAB_VALIDATION,
    )
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
        provenance=_provenance(execution_custody=_custody()),
        policy=_policy(human_approval_required=True),
    )
    assert envelope.state == BoundaryState.AWAITING_HUMAN_APPROVAL
    assert envelope.action.capability_status == CapabilityStatus.REQUIRES_LAB_VALIDATION


def test_evidence_payload_binds_exact_action_without_logging_raw_parameters():
    action = _software_action(parameters={"sensitive_parameter": "do-not-copy-to-event"})
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=_context(),
        provenance=_provenance(),
        policy=_policy(),
    )
    payload = boundary_event_payload(envelope)

    assert "parameters" not in payload
    assert payload["action_digest"] == envelope.action_digest
    assert payload["envelope_digest"] == envelope.envelope_digest
    assert payload["capability_status"] == CapabilityStatus.IMPLEMENTED_IN_SOFTWARE.value
    assert "Raw action parameters" in payload["privacy_boundary"]


def test_boundary_transition_queues_through_existing_at_least_once_outbox():
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=_software_action(),
        context=_context(),
        provenance=_provenance(),
        policy=_policy(),
    )
    patch, event_id = queue_boundary_transition({}, envelope)
    assert event_id.startswith("SARA-EVENT-")
    entry = patch[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert entry["status"] == "PENDING"
    assert entry["delivery_semantics"] == "AT_LEAST_ONCE"
    assert entry["payload"]["envelope_digest"] == envelope.envelope_digest


def test_programmable_boundary_benchmark_enters_kernel_as_simulation_only():
    report = run_programmable_boundary_benchmark()
    action = build_programmable_boundary_simulation_action(
        report,
        scenario_id="coherent_target",
    )
    assert action.domain == BoundaryDomain.PROGRAMMABLE_BOUNDARY
    assert action.effect_scope == EvidenceScope.SIMULATION
    assert action.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert action.parameters["benchmark_report_digest"] == report.report_digest

    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=action,
        context=BoundaryContext(environment=BoundaryEnvironment.SIMULATION),
        provenance=BoundaryProvenance(
            agent_version="ws-programmable-boundary-benchmark",
            source_evidence_refs=(report.qualification_id,),
        ),
        policy=_policy(
            reasons=("Synthetic benchmark is bounded to SIMULATION scope.",),
        ),
    )
    assert envelope.state == BoundaryState.AUTHORIZED
    assert verify_boundary_envelope(envelope) is True

    promoted = action.model_copy(update={"effect_scope": EvidenceScope.PHYSICAL})
    with pytest.raises(ValidationError, match="SIMULATED_ONLY"):
        create_boundary_envelope(
            actor="SSPADAWANZZ",
            action=promoted,
            context=BoundaryContext(environment=BoundaryEnvironment.LAB_TEST),
            provenance=_provenance(execution_custody=_custody()),
            policy=_policy(human_approval_required=True),
        )


def test_envelope_tamper_is_detected():
    envelope = create_boundary_envelope(
        actor="SSPADAWANZZ",
        action=_software_action(),
        context=_context(),
        provenance=_provenance(),
        policy=_policy(),
    )
    tampered = envelope.model_copy(update={"actor": "UNBOUND-ACTOR"})
    assert verify_boundary_envelope(tampered) is False
