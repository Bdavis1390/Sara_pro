"""Claims-controlled audit projections for Worldshepherd Proof of Ownership.

The projection layer turns ownership, transfer, and recovery decisions into a
uniform governance record. It carries readiness/evidence state only and never
conveys execution authority or legal-title adjudication.
"""

from __future__ import annotations

from typing import Dict

from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.transfer_guard import TransferEvidence, evaluate_transfer
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery

POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V1"
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
    technical_attestation_ready: bool,
    transfer_ready: bool,
    recovery_ready: bool,
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
        "transfer_ready": transfer_ready,
        "recovery_ready": recovery_ready,
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
    if decision.poo_valid:
        states = (
            "ECHO_POO_EVIDENCE_ACCEPTED",
            "PRIME_POO_ATTESTATION_READY",
            "SARA_POO_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_MONITOR_ACTIVE",
        )
    else:
        states = (
            "ECHO_POO_EVIDENCE_INCOMPLETE",
            "PRIME_POO_BLOCKED",
            "SARA_POO_BLOCKED",
            "OVERWATCH_POO_EVIDENCE_GAP",
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
        transfer_ready=False,
        recovery_ready=False,
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
        technical_attestation_ready=False,
        transfer_ready=decision.transfer_ready,
        recovery_ready=False,
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
        technical_attestation_ready=False,
        transfer_ready=False,
        recovery_ready=decision.recovery_ready,
    )
