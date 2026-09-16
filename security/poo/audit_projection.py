"""Claims-controlled audit projections for Worldshepherd Proof of Ownership.

Governance Decision V3 preserves the existing ownership/COC/transfer/recovery/state/
registry projections and adds explicit full-state-lineage and optimistic-concurrency
commit-readiness evidence. Audit projections remain non-executing and never adjudicate
legal title, perform a durable registry write, or select a winner in a conflict.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from typing import Dict

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery
from security.poo.registry_governance_guard import GovernedRegistryCommitDecision
from security.poo.registry_guard import RegistryDecision
from security.poo.state_engine import StateLineageDecision, StateTransitionDecision
from security.poo.state_governance_guard import GovernedStateTransitionDecision
from security.poo.transfer_guard import TransferEvidence, evaluate_transfer

POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V3"
POO_CLAIM_BOUNDARY = "INTERNAL_POO_EVIDENCE_NOT_LEGAL_TITLE_OR_EXECUTION_AUTHORITY"


def _base_projection(
    *,
    operation: str,
    asset_id: str,
    source_digest: str,
    status: str,
    echo_state: str,
    prime_state: str,
    sara_state: str,
    overwatch_state: str,
    previous_poo_digest: str | None,
    technical_attestation_ready: bool = False,
    coc_valid: bool = False,
    transfer_ready: bool = False,
    recovery_ready: bool = False,
    state_transition_ready: bool = False,
    registry_consistent: bool = False,
    state_lineage_checked: bool = False,
    state_lineage_valid: bool = False,
    poo_lineage_valid: bool = False,
    coc_lineage_valid: bool = False,
    generation_valid: bool = False,
    fork_detected: bool = False,
    cycle_detected: bool = False,
    active_tip_digest: str | None = None,
    lineage_issue_count: int = 0,
    registry_commit_ready: bool = False,
    optimistic_concurrency_checked: bool = False,
    optimistic_concurrency_match: bool = False,
    expected_registry_digest: str | None = None,
    current_registry_digest: str | None = None,
    candidate_registry_digest: str | None = None,
    candidate_state_digest: str | None = None,
) -> Dict[str, object]:
    return {
        "schema": POO_AUDIT_SCHEMA,
        "operation": operation,
        "asset_id": asset_id,
        "source_digest": source_digest,
        "source_status": status,
        "previous_poo_digest": previous_poo_digest,
        "echo_state": echo_state,
        "prime_state": prime_state,
        "sara_state": sara_state,
        "overwatch_state": overwatch_state,
        "technical_attestation_ready": technical_attestation_ready,
        "coc_valid": coc_valid,
        "transfer_ready": transfer_ready,
        "recovery_ready": recovery_ready,
        "state_transition_ready": state_transition_ready,
        "registry_consistent": registry_consistent,
        "state_lineage_checked": state_lineage_checked,
        "state_lineage_valid": state_lineage_valid,
        "poo_lineage_valid": poo_lineage_valid,
        "coc_lineage_valid": coc_lineage_valid,
        "generation_valid": generation_valid,
        "fork_detected": fork_detected,
        "cycle_detected": cycle_detected,
        "active_tip_digest": active_tip_digest,
        "lineage_issue_count": lineage_issue_count,
        "registry_commit_ready": registry_commit_ready,
        "optimistic_concurrency_checked": optimistic_concurrency_checked,
        "optimistic_concurrency_match": optimistic_concurrency_match,
        "expected_registry_digest": expected_registry_digest,
        "current_registry_digest": current_registry_digest,
        "candidate_registry_digest": candidate_registry_digest,
        "candidate_state_digest": candidate_state_digest,
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "technical_registry_committed": False,
        "durable_registry_write_authorized": False,
        "conflict_winner_selected": False,
        "lineage_auto_resolved": False,
        "claim_boundary": POO_CLAIM_BOUNDARY,
    }


def ownership_audit_projection(evidence: OwnershipEvidence) -> Dict[str, object]:
    decision = evaluate_ownership(evidence)
    states = (
        (
            "ECHO_POO_EVIDENCE_ACCEPTED",
            "PRIME_POO_ATTESTATION_READY",
            "SARA_POO_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_MONITOR_ACTIVE",
        )
        if decision.poo_valid
        else (
            "ECHO_POO_EVIDENCE_INCOMPLETE",
            "PRIME_POO_BLOCKED",
            "SARA_POO_BLOCKED",
            "OVERWATCH_POO_EVIDENCE_GAP",
        )
    )
    return _base_projection(
        operation="OWNERSHIP_ATTESTATION",
        asset_id=evidence.asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=evidence.previous_poo_digest,
        technical_attestation_ready=decision.poo_valid,
    )


def coc_audit_projection(evidence: COCEvidence) -> Dict[str, object]:
    decision = evaluate_coc(evidence)
    states = (
        (
            "ECHO_COC_EVIDENCE_ACCEPTED",
            "PRIME_COC_ACCEPTED",
            "SARA_COC_HUMAN_REVIEW_READY",
            "OVERWATCH_COC_MONITOR_ACTIVE",
        )
        if decision.coc_valid
        else (
            "ECHO_COC_EVIDENCE_INCOMPLETE",
            "PRIME_COC_BLOCKED",
            "SARA_COC_BLOCKED",
            "OVERWATCH_COC_EVIDENCE_GAP",
        )
    )
    return _base_projection(
        operation="COC_ATTESTATION",
        asset_id=evidence.asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=None,
        coc_valid=decision.coc_valid,
    )


def transfer_audit_projection(evidence: TransferEvidence) -> Dict[str, object]:
    decision = evaluate_transfer(evidence)
    if decision.transfer_ready:
        states = (
            "ECHO_POO_TRANSFER_EVIDENCE_ACCEPTED",
            "PRIME_POO_TRANSFER_READY",
            "SARA_POO_TRANSFER_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_TRANSFER_PENDING_SUPERSESSION",
        )
    elif decision.status == "TRANSFER_DISPUTED_BLOCKED":
        states = (
            "ECHO_POO_TRANSFER_DISPUTE_RECORDED",
            "PRIME_POO_TRANSFER_BLOCKED_DISPUTE",
            "SARA_POO_TRANSFER_BLOCKED",
            "OVERWATCH_POO_DISPUTE_ACTIVE",
        )
    else:
        states = (
            "ECHO_POO_TRANSFER_EVIDENCE_INCOMPLETE",
            "PRIME_POO_TRANSFER_BLOCKED",
            "SARA_POO_TRANSFER_BLOCKED",
            "OVERWATCH_POO_TRANSFER_EVIDENCE_GAP",
        )
    return _base_projection(
        operation="TRANSFER_READINESS",
        asset_id=evidence.asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=evidence.prior_poo_digest,
        transfer_ready=decision.transfer_ready,
    )


def recovery_audit_projection(evidence: RecoveryEvidence) -> Dict[str, object]:
    decision = evaluate_recovery(evidence)
    if decision.recovery_ready:
        states = (
            "ECHO_POO_RECOVERY_EVIDENCE_ACCEPTED",
            "PRIME_POO_RECOVERY_READY",
            "SARA_POO_RECOVERY_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_RECOVERY_PENDING_SUPERSESSION",
        )
    elif decision.status == "RECOVERY_DISPUTE_REVIEW_REQUIRED":
        states = (
            "ECHO_POO_RECOVERY_DISPUTE_RECORDED",
            "PRIME_POO_RECOVERY_BLOCKED_DISPUTE",
            "SARA_POO_RECOVERY_BLOCKED",
            "OVERWATCH_POO_DISPUTE_ACTIVE",
        )
    else:
        states = (
            "ECHO_POO_RECOVERY_EVIDENCE_INCOMPLETE",
            "PRIME_POO_RECOVERY_BLOCKED",
            "SARA_POO_RECOVERY_BLOCKED",
            "OVERWATCH_POO_RECOVERY_EVIDENCE_GAP",
        )
    return _base_projection(
        operation="RECOVERY_READINESS",
        asset_id=evidence.asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=evidence.prior_poo_digest,
        recovery_ready=decision.recovery_ready,
    )


def _transition_digest(decision: StateTransitionDecision) -> str:
    raw = json.dumps(asdict(decision), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def state_transition_audit_projection(
    decision: StateTransitionDecision,
    *,
    asset_id: str,
    previous_poo_digest: str | None,
) -> Dict[str, object]:
    """Project a local candidate-state result; this is not commit readiness."""
    states = (
        (
            "ECHO_POO_STATE_CANDIDATE_ACCEPTED",
            "PRIME_POO_LOCAL_STATE_CANDIDATE_READY",
            "SARA_POO_LOCAL_STATE_REVIEW_ONLY",
            "OVERWATCH_POO_STATE_CANDIDATE_MONITOR",
        )
        if decision.ready
        else (
            "ECHO_POO_STATE_TRANSITION_BLOCKED",
            "PRIME_POO_STATE_TRANSITION_BLOCKED",
            "SARA_POO_STATE_TRANSITION_BLOCKED",
            "OVERWATCH_POO_STATE_REVIEW_REQUIRED",
        )
    )
    return _base_projection(
        operation="TECHNICAL_STATE_TRANSITION",
        asset_id=asset_id,
        source_digest=_transition_digest(decision),
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=previous_poo_digest,
        state_transition_ready=decision.ready,
        candidate_state_digest=decision.candidate_state_digest,
    )


def _conflict_type(decision: StateLineageDecision) -> str:
    if decision.lineage_valid:
        return "NONE"
    if decision.fork_detected and decision.cycle_detected:
        return "MULTIPLE"
    if decision.fork_detected:
        return "FORK"
    if decision.cycle_detected:
        return "CYCLE"
    if not decision.coc_lineage_valid:
        return "COC_LINEAGE"
    if not decision.generation_valid:
        return "GENERATION"
    return "STRUCTURAL"


def state_lineage_audit_projection(
    decision: StateLineageDecision,
    *,
    asset_id: str,
) -> Dict[str, object]:
    if decision.lineage_valid:
        states = (
            "ECHO_POO_STATE_LINEAGE_ACCEPTED",
            "PRIME_POO_STATE_LINEAGE_ELIGIBLE",
            "SARA_POO_STATE_LINEAGE_MONITORABLE",
            "OVERWATCH_POO_STATE_LINEAGE_HEALTHY",
        )
    else:
        states = (
            "ECHO_POO_STATE_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_STATE_LINEAGE_BLOCKED",
            "SARA_POO_STATE_LINEAGE_DISPUTE_BLOCK",
            "OVERWATCH_POO_STATE_LINEAGE_CONFLICT_ACTIVE",
        )
    return _base_projection(
        operation="STATE_LINEAGE_INTEGRITY",
        asset_id=asset_id,
        source_digest=decision.digest,
        status=decision.status + ":" + _conflict_type(decision),
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=None,
        state_lineage_checked=True,
        state_lineage_valid=decision.lineage_valid,
        poo_lineage_valid=decision.poo_lineage_valid,
        coc_lineage_valid=decision.coc_lineage_valid,
        generation_valid=decision.generation_valid,
        fork_detected=decision.fork_detected,
        cycle_detected=decision.cycle_detected,
        active_tip_digest=decision.active_tip_digest,
        lineage_issue_count=len(decision.issues),
    )


def governed_state_transition_audit_projection(
    decision: GovernedStateTransitionDecision,
    *,
    asset_id: str,
    previous_poo_digest: str | None,
) -> Dict[str, object]:
    if decision.ready:
        states = (
            "ECHO_POO_GOVERNED_STATE_CANDIDATE_ACCEPTED",
            "PRIME_POO_GOVERNED_STATE_TRANSITION_READY",
            "SARA_POO_GOVERNED_STATE_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_GOVERNED_STATE_PENDING_COMMIT",
        )
    elif not decision.state_lineage_valid:
        states = (
            "ECHO_POO_STATE_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_GOVERNED_STATE_BLOCKED_LINEAGE",
            "SARA_POO_GOVERNED_STATE_DISPUTE_BLOCK",
            "OVERWATCH_POO_STATE_LINEAGE_CONFLICT_ACTIVE",
        )
    else:
        states = (
            "ECHO_POO_GOVERNED_STATE_BLOCKED",
            "PRIME_POO_GOVERNED_STATE_BLOCKED",
            "SARA_POO_GOVERNED_STATE_BLOCKED",
            "OVERWATCH_POO_GOVERNED_STATE_REVIEW_REQUIRED",
        )
    return _base_projection(
        operation="GOVERNED_STATE_TRANSITION",
        asset_id=asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=previous_poo_digest,
        state_transition_ready=decision.ready,
        state_lineage_checked=decision.state_lineage_checked,
        state_lineage_valid=decision.state_lineage_valid,
        poo_lineage_valid=decision.poo_lineage_valid,
        coc_lineage_valid=decision.coc_lineage_valid,
        generation_valid=decision.generation_valid,
        fork_detected=decision.fork_detected,
        cycle_detected=decision.cycle_detected,
        active_tip_digest=decision.active_tip_poo_digest,
        lineage_issue_count=decision.lineage_issue_count,
        candidate_state_digest=decision.candidate_state_digest,
    )


def registry_audit_projection(decision: RegistryDecision) -> Dict[str, object]:
    states = (
        (
            "ECHO_POO_REGISTRY_SNAPSHOT_ACCEPTED",
            "PRIME_POO_REGISTRY_CONSISTENT",
            "SARA_POO_REGISTRY_REVIEW_READY",
            "OVERWATCH_POO_REGISTRY_HEALTHY",
        )
        if decision.registry_valid
        else (
            "ECHO_POO_REGISTRY_REVIEW_REQUIRED",
            "PRIME_POO_REGISTRY_INCONSISTENT",
            "SARA_POO_REGISTRY_REVIEW_REQUIRED",
            "OVERWATCH_POO_REGISTRY_CONFLICT",
        )
    )
    return _base_projection(
        operation="REGISTRY_HEALTH",
        asset_id="registry:technical-ownership",
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=None,
        registry_consistent=decision.registry_valid,
    )


def registry_commit_readiness_audit_projection(
    decision: GovernedRegistryCommitDecision,
    *,
    asset_id: str,
    previous_poo_digest: str | None,
) -> Dict[str, object]:
    if decision.ready:
        states = (
            "ECHO_POO_REGISTRY_COMMIT_EVIDENCE_ACCEPTED",
            "PRIME_POO_REGISTRY_COMMIT_CANDIDATE_READY",
            "SARA_POO_REGISTRY_COMMIT_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_REGISTRY_COMMIT_PENDING",
        )
    elif not decision.state_lineage_valid:
        states = (
            "ECHO_POO_STATE_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_REGISTRY_COMMIT_BLOCKED_LINEAGE",
            "SARA_POO_REGISTRY_COMMIT_DISPUTE_BLOCK",
            "OVERWATCH_POO_STATE_LINEAGE_CONFLICT_ACTIVE",
        )
    elif not decision.optimistic_concurrency_match:
        states = (
            "ECHO_POO_REGISTRY_STALE_SNAPSHOT_RECORDED",
            "PRIME_POO_REGISTRY_COMMIT_BLOCKED_STALE",
            "SARA_POO_REGISTRY_COMMIT_REEVALUATION_REQUIRED",
            "OVERWATCH_POO_REGISTRY_STALE_SNAPSHOT_ALERT",
        )
    else:
        states = (
            "ECHO_POO_REGISTRY_COMMIT_BLOCKED",
            "PRIME_POO_REGISTRY_COMMIT_BLOCKED",
            "SARA_POO_REGISTRY_COMMIT_BLOCKED",
            "OVERWATCH_POO_REGISTRY_COMMIT_REVIEW_REQUIRED",
        )
    return _base_projection(
        operation="REGISTRY_COMMIT_READINESS",
        asset_id=asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=previous_poo_digest,
        state_lineage_checked=decision.state_lineage_checked,
        state_lineage_valid=decision.state_lineage_valid,
        poo_lineage_valid=decision.poo_lineage_valid,
        coc_lineage_valid=decision.coc_lineage_valid,
        generation_valid=decision.generation_valid,
        fork_detected=decision.fork_detected,
        cycle_detected=decision.cycle_detected,
        active_tip_digest=decision.active_tip_poo_digest,
        lineage_issue_count=decision.lineage_issue_count,
        registry_commit_ready=decision.ready,
        optimistic_concurrency_checked=decision.optimistic_concurrency_checked,
        optimistic_concurrency_match=decision.optimistic_concurrency_match,
        expected_registry_digest=decision.expected_registry_digest,
        current_registry_digest=decision.current_registry_digest,
        candidate_registry_digest=decision.candidate_registry_digest,
        candidate_state_digest=decision.candidate_state_digest,
    )
