"""Claims-controlled audit projections for Worldshepherd Proof of Ownership.

The projection layer turns ownership, transfer, recovery, and lineage decisions into
one uniform governance record. Transfer/recovery readiness is lineage-governed: base
PoW/PoC/COC/PoS readiness cannot be promoted unless the referenced predecessor is the
single active technical PoO tip. The layer never conveys execution authority,
automatic conflict resolution, or legal-title adjudication.
"""

from __future__ import annotations

from typing import Dict, Iterable

from security.poo.governance_guard import (
    evaluate_governed_recovery,
    evaluate_governed_transfer,
)
from security.poo.lineage_guard import LineageNode, evaluate_lineage
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery
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
    technical_attestation_ready: bool,
    transfer_ready: bool,
    recovery_ready: bool,
    lineage_checked: bool = False,
    lineage_valid: bool = False,
    fork_detected: bool = False,
    cycle_detected: bool = False,
    active_tip_digest: str | None = None,
    lineage_issue_count: int = 0,
    lineage_conflict_type: str = "NONE",
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
        "lineage_checked": lineage_checked,
        "lineage_valid": lineage_valid,
        "fork_detected": fork_detected,
        "cycle_detected": cycle_detected,
        "active_tip_digest": active_tip_digest,
        "lineage_issue_count": lineage_issue_count,
        "lineage_conflict_type": lineage_conflict_type,
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "conflict_winner_selected": False,
        "lineage_auto_resolved": False,
        "claim_boundary": POO_CLAIM_BOUNDARY,
    }


def _lineage_conflict_type(*, valid: bool, fork: bool, cycle: bool) -> str:
    if valid:
        return "NONE"
    if fork and cycle:
        return "MULTIPLE"
    if fork:
        return "FORK"
    if cycle:
        return "CYCLE"
    return "STRUCTURAL"


def _lineage_projection_fields(nodes: list[LineageNode]) -> dict[str, object]:
    decision = evaluate_lineage(nodes)
    return {
        "lineage_checked": True,
        "lineage_valid": decision.lineage_valid,
        "fork_detected": decision.fork_detected,
        "cycle_detected": decision.cycle_detected,
        "active_tip_digest": decision.active_tip_digest,
        "lineage_issue_count": len(decision.issues),
        "lineage_conflict_type": _lineage_conflict_type(
            valid=decision.lineage_valid,
            fork=decision.fork_detected,
            cycle=decision.cycle_detected,
        ),
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


def transfer_audit_projection(
    evidence: TransferEvidence,
    lineage_nodes: Iterable[LineageNode],
) -> Dict[str, object]:
    nodes = list(lineage_nodes)
    base = evaluate_transfer(evidence)
    governed = evaluate_governed_transfer(evidence, nodes)
    lineage = evaluate_lineage(nodes)

    if governed.readiness_allowed:
        states = (
            "ECHO_POO_TRANSFER_EVIDENCE_ACCEPTED",
            "PRIME_POO_TRANSFER_READY",
            "SARA_POO_TRANSFER_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_TRANSFER_PENDING_SUPERSESSION",
        )
    elif not lineage.lineage_valid:
        states = (
            "ECHO_POO_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_TRANSFER_BLOCKED_LINEAGE",
            "SARA_POO_TRANSFER_DISPUTE_BLOCK",
            "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE",
        )
    elif governed.status in {"STALE_LINEAGE_REFERENCE_BLOCKED", "ACTIVE_TIP_CLAIMANT_MISMATCH"}:
        states = (
            "ECHO_POO_TRANSFER_LINEAGE_MISMATCH_RECORDED",
            "PRIME_POO_TRANSFER_BLOCKED_LINEAGE",
            "SARA_POO_TRANSFER_BLOCKED",
            "OVERWATCH_POO_LINEAGE_REFERENCE_ALERT",
        )
    elif base.status == "TRANSFER_DISPUTED_BLOCKED":
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
        source_digest=governed.digest,
        status=governed.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=evidence.prior_poo_digest,
        technical_attestation_ready=False,
        transfer_ready=governed.readiness_allowed,
        recovery_ready=False,
        **_lineage_projection_fields(nodes),
    )


def recovery_audit_projection(
    evidence: RecoveryEvidence,
    lineage_nodes: Iterable[LineageNode],
) -> Dict[str, object]:
    nodes = list(lineage_nodes)
    base = evaluate_recovery(evidence)
    governed = evaluate_governed_recovery(evidence, nodes)
    lineage = evaluate_lineage(nodes)

    if governed.readiness_allowed:
        states = (
            "ECHO_POO_RECOVERY_EVIDENCE_ACCEPTED",
            "PRIME_POO_RECOVERY_READY",
            "SARA_POO_RECOVERY_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_RECOVERY_PENDING_SUPERSESSION",
        )
    elif not lineage.lineage_valid:
        states = (
            "ECHO_POO_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_RECOVERY_BLOCKED_LINEAGE",
            "SARA_POO_RECOVERY_DISPUTE_BLOCK",
            "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE",
        )
    elif governed.status in {"STALE_LINEAGE_REFERENCE_BLOCKED", "ACTIVE_TIP_CLAIMANT_MISMATCH"}:
        states = (
            "ECHO_POO_RECOVERY_LINEAGE_MISMATCH_RECORDED",
            "PRIME_POO_RECOVERY_BLOCKED_LINEAGE",
            "SARA_POO_RECOVERY_BLOCKED",
            "OVERWATCH_POO_LINEAGE_REFERENCE_ALERT",
        )
    elif base.status == "RECOVERY_DISPUTE_REVIEW_REQUIRED":
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
        source_digest=governed.digest,
        status=governed.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=evidence.prior_poo_digest,
        technical_attestation_ready=False,
        transfer_ready=False,
        recovery_ready=governed.readiness_allowed,
        **_lineage_projection_fields(nodes),
    )


def lineage_audit_projection(nodes: Iterable[LineageNode]) -> Dict[str, object]:
    records = list(nodes)
    decision = evaluate_lineage(records)
    asset_ids = sorted({node.asset_id for node in records if node.asset_id})
    asset_id = asset_ids[0] if len(asset_ids) == 1 else "LINEAGE_ASSET_UNRESOLVED"

    if decision.lineage_valid:
        states = (
            "ECHO_POO_LINEAGE_ACCEPTED",
            "PRIME_POO_LINEAGE_ELIGIBLE",
            "SARA_POO_LINEAGE_MONITORABLE",
            "OVERWATCH_POO_LINEAGE_HEALTHY",
        )
    else:
        states = (
            "ECHO_POO_LINEAGE_CONFLICT_CUSTODIED",
            "PRIME_POO_LINEAGE_BLOCKED",
            "SARA_POO_LINEAGE_DISPUTE_BLOCK",
            "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE",
        )

    return _base_projection(
        operation="LINEAGE_INTEGRITY",
        asset_id=asset_id,
        source_digest=decision.digest,
        status=decision.status,
        echo_state=states[0],
        prime_state=states[1],
        sara_state=states[2],
        overwatch_state=states[3],
        previous_poo_digest=None,
        technical_attestation_ready=False,
        transfer_ready=False,
        recovery_ready=False,
        **_lineage_projection_fields(records),
    )
