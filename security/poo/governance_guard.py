"""Worldshepherd PoO lineage-governed readiness guard.

This layer composes otherwise-valid transfer/recovery evidence with the technical PoO
lineage. It blocks stale-predecessor, forked-lineage, and active-tip claimant mismatches.
It never executes a transfer, rotates control, selects a conflict winner, or adjudicates
legal title.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

from security.poo.lineage_guard import LineageNode, evaluate_lineage
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery
from security.poo.transfer_guard import TransferEvidence, evaluate_transfer

GOVERNANCE_SCHEMA = "WS-POO-LINEAGE-GOVERNANCE-V1"


@dataclass(frozen=True)
class GovernedReadinessDecision:
    schema: str
    operation: str
    status: str
    readiness_allowed: bool
    base_readiness: bool
    lineage_valid: bool
    active_tip_digest: Optional[str]
    active_tip_claimant_id: Optional[str]
    missing_predicates: List[str]
    digest: str
    transfer_executed: bool
    control_rotated: bool
    live_value_authorized: bool
    legal_title_changed: bool
    conflict_winner_selected: bool
    lineage_auto_resolved: bool
    claims_boundary: Dict[str, bool]


def _active_tip(nodes: list[LineageNode], digest: Optional[str]) -> Optional[LineageNode]:
    if digest is None:
        return None
    for node in nodes:
        if node.poo_digest == digest:
            return node
    return None


def _governance_digest(
    *,
    operation: str,
    base_digest: str,
    lineage_digest: str,
    active_tip_digest: Optional[str],
) -> str:
    payload = {
        "schema": GOVERNANCE_SCHEMA,
        "operation": operation,
        "base_digest": base_digest,
        "lineage_digest": lineage_digest,
        "active_tip_digest": active_tip_digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _decision(
    *,
    operation: str,
    status: str,
    readiness_allowed: bool,
    base_readiness: bool,
    lineage_valid: bool,
    active_tip: Optional[LineageNode],
    missing: list[str],
    digest: str,
) -> GovernedReadinessDecision:
    return GovernedReadinessDecision(
        schema=GOVERNANCE_SCHEMA,
        operation=operation,
        status=status,
        readiness_allowed=readiness_allowed,
        base_readiness=base_readiness,
        lineage_valid=lineage_valid,
        active_tip_digest=active_tip.poo_digest if active_tip else None,
        active_tip_claimant_id=active_tip.claimant_id if active_tip else None,
        missing_predicates=missing,
        digest=digest,
        transfer_executed=False,
        control_rotated=False,
        live_value_authorized=False,
        legal_title_changed=False,
        conflict_winner_selected=False,
        lineage_auto_resolved=False,
        claims_boundary={
            "technical_lineage_only": True,
            "legal_title_adjudication": False,
            "government_registry_authority": False,
            "automatic_transfer_execution": False,
            "automatic_control_rotation": False,
            "automatic_conflict_resolution": False,
            "conflict_winner_selection": False,
            "live_value_movement": False,
        },
    )


def evaluate_governed_transfer(
    transfer: TransferEvidence,
    lineage_nodes: Iterable[LineageNode],
) -> GovernedReadinessDecision:
    nodes = list(lineage_nodes)
    base = evaluate_transfer(transfer)
    lineage = evaluate_lineage(nodes)
    tip = _active_tip(nodes, lineage.active_tip_digest) if lineage.lineage_valid else None
    missing: list[str] = []

    if not base.transfer_ready:
        missing.append("base transfer evidence not ready")
    if not lineage.lineage_valid:
        missing.append("lineage integrity not verified")
    if tip is not None:
        if transfer.prior_poo_digest != tip.poo_digest:
            missing.append("transfer prior PoO is not active lineage tip")
        if transfer.asset_id != tip.asset_id:
            missing.append("transfer asset does not match active lineage tip")
        if transfer.current_owner_id != tip.claimant_id:
            missing.append("current owner does not match active technical lineage tip")

    ready = not missing
    if not lineage.lineage_valid:
        status = "LINEAGE_CONFLICT_BLOCKED"
    elif transfer.prior_poo_digest != (tip.poo_digest if tip else None):
        status = "STALE_LINEAGE_REFERENCE_BLOCKED"
    elif tip is not None and transfer.current_owner_id != tip.claimant_id:
        status = "ACTIVE_TIP_CLAIMANT_MISMATCH"
    elif not base.transfer_ready:
        status = "BASE_TRANSFER_NOT_READY"
    elif ready:
        status = "TRANSFER_READY_WITH_LINEAGE_GUARD"
    else:
        status = "TRANSFER_GOVERNANCE_BLOCKED"

    return _decision(
        operation="TRANSFER_READINESS",
        status=status,
        readiness_allowed=ready,
        base_readiness=base.transfer_ready,
        lineage_valid=lineage.lineage_valid,
        active_tip=tip,
        missing=missing,
        digest=_governance_digest(
            operation="TRANSFER_READINESS",
            base_digest=base.digest,
            lineage_digest=lineage.digest,
            active_tip_digest=lineage.active_tip_digest,
        ),
    )


def evaluate_governed_recovery(
    recovery: RecoveryEvidence,
    lineage_nodes: Iterable[LineageNode],
) -> GovernedReadinessDecision:
    nodes = list(lineage_nodes)
    base = evaluate_recovery(recovery)
    lineage = evaluate_lineage(nodes)
    tip = _active_tip(nodes, lineage.active_tip_digest) if lineage.lineage_valid else None
    missing: list[str] = []

    if not base.recovery_ready:
        missing.append("base recovery evidence not ready")
    if not lineage.lineage_valid:
        missing.append("lineage integrity not verified")
    if tip is not None:
        if recovery.prior_poo_digest != tip.poo_digest:
            missing.append("recovery prior PoO is not active lineage tip")
        if recovery.asset_id != tip.asset_id:
            missing.append("recovery asset does not match active lineage tip")
        if recovery.claimant_id != tip.claimant_id:
            missing.append("recovery claimant does not match active technical lineage tip")

    ready = not missing
    if not lineage.lineage_valid:
        status = "LINEAGE_CONFLICT_BLOCKED"
    elif recovery.prior_poo_digest != (tip.poo_digest if tip else None):
        status = "STALE_LINEAGE_REFERENCE_BLOCKED"
    elif tip is not None and recovery.claimant_id != tip.claimant_id:
        status = "ACTIVE_TIP_CLAIMANT_MISMATCH"
    elif not base.recovery_ready:
        status = "BASE_RECOVERY_NOT_READY"
    elif ready:
        status = "RECOVERY_READY_WITH_LINEAGE_GUARD"
    else:
        status = "RECOVERY_GOVERNANCE_BLOCKED"

    return _decision(
        operation="RECOVERY_READINESS",
        status=status,
        readiness_allowed=ready,
        base_readiness=base.recovery_ready,
        lineage_valid=lineage.lineage_valid,
        active_tip=tip,
        missing=missing,
        digest=_governance_digest(
            operation="RECOVERY_READINESS",
            base_digest=base.digest,
            lineage_digest=lineage.digest,
            active_tip_digest=lineage.active_tip_digest,
        ),
    )
