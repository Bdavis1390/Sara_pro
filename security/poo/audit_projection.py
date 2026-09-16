"""Claims-controlled audit projections for Worldshepherd Proof of Ownership.

The projection layer turns ownership, COC, transfer, recovery, technical-state,
and registry decisions into a uniform governance record. It carries readiness and
evidence state only and never conveys execution authority or legal-title adjudication.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from typing import Dict

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery
from security.poo.registry_guard import RegistryDecision
from security.poo.state_engine import StateTransitionDecision
from security.poo.transfer_guard import TransferEvidence, evaluate_transfer

POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V2"
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
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
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
    raw = json.dumps(
        asdict(decision), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def state_transition_audit_projection(
    decision: StateTransitionDecision,
    *,
    asset_id: str,
    previous_poo_digest: str | None,
) -> Dict[str, object]:
    states = (
        (
            "ECHO_POO_STATE_CANDIDATE_ACCEPTED",
            "PRIME_POO_STATE_TRANSITION_READY",
            "SARA_POO_STATE_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_STATE_PENDING_COMMIT",
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
