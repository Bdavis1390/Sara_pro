"""State-lineage governance for Worldshepherd Proof of Ownership.

This layer composes the existing PoO technical-state engine with full historical
state-lineage verification. A transfer/recovery may satisfy its local PoW/PoC/COC/PoS
requirements yet remain blocked when the historical PoO, COC, or generation lineage is
inconsistent. This module prepares evidence only; it never commits registry state,
changes legal title, rotates credentials, moves value, or selects a conflict winner.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.recovery_guard import RecoveryEvidence, evaluate_recovery
from security.poo.state_engine import (
    StateLineageDecision,
    StateTransitionDecision,
    TechnicalOwnershipState,
    evaluate_state_lineage,
    prepare_recovery_transition,
    prepare_transfer_transition,
    state_digest,
)
from security.poo.transfer_guard import TransferEvidence, evaluate_transfer

STATE_GOVERNANCE_SCHEMA = "WS-POO-STATE-GOVERNANCE-V1"


@dataclass(frozen=True)
class GovernedStateTransitionDecision:
    schema: str
    operation: str
    status: str
    ready: bool
    base_evidence_ready: bool
    state_lineage_checked: bool
    state_lineage_valid: bool
    poo_lineage_valid: bool
    coc_lineage_valid: bool
    generation_valid: bool
    fork_detected: bool
    cycle_detected: bool
    active_tip_poo_digest: Optional[str]
    active_tip_state_digest: Optional[str]
    lineage_issue_count: int
    reasons: List[str]
    transition: Optional[StateTransitionDecision]
    candidate_state_digest: Optional[str]
    digest: str
    technical_state_committed: bool
    conflict_winner_selected: bool
    lineage_auto_resolved: bool
    legal_title_changed: bool
    live_value_moved: bool
    external_transfer_executed: bool
    claims_boundary: Dict[str, bool]


def _boundary() -> Dict[str, bool]:
    return {
        "technical_lineage_only": True,
        "government_registry_authority": False,
        "legal_title_adjudication": False,
        "durable_registry_write_authority": False,
        "credential_rotation_authority": False,
        "conflict_winner_selection": False,
        "automatic_lineage_resolution": False,
        "live_value_movement": False,
        "external_transfer_execution": False,
        "external_validation_established": False,
    }


def _active_state(
    states: list[TechnicalOwnershipState],
    lineage: StateLineageDecision,
) -> Optional[TechnicalOwnershipState]:
    if not lineage.lineage_valid or not lineage.active_tip_digest:
        return None
    matches = [state for state in states if state.active_poo_digest == lineage.active_tip_digest]
    return matches[0] if len(matches) == 1 else None


def _decision_digest(
    *,
    operation: str,
    lineage: StateLineageDecision,
    base_digest: str,
    active_state: Optional[TechnicalOwnershipState],
    candidate_state_digest: Optional[str],
) -> str:
    payload = {
        "schema": STATE_GOVERNANCE_SCHEMA,
        "operation": operation,
        "state_lineage_digest": lineage.digest,
        "base_evidence_digest": base_digest,
        "active_tip_poo_digest": lineage.active_tip_digest,
        "active_tip_state_digest": state_digest(active_state) if active_state else None,
        "candidate_state_digest": candidate_state_digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _result(
    *,
    operation: str,
    status: str,
    ready: bool,
    base_evidence_ready: bool,
    lineage: StateLineageDecision,
    active_state: Optional[TechnicalOwnershipState],
    reasons: List[str],
    transition: Optional[StateTransitionDecision],
    base_digest: str,
) -> GovernedStateTransitionDecision:
    candidate_digest = transition.candidate_state_digest if transition is not None else None
    return GovernedStateTransitionDecision(
        schema=STATE_GOVERNANCE_SCHEMA,
        operation=operation,
        status=status,
        ready=ready,
        base_evidence_ready=base_evidence_ready,
        state_lineage_checked=True,
        state_lineage_valid=lineage.lineage_valid,
        poo_lineage_valid=lineage.poo_lineage_valid,
        coc_lineage_valid=lineage.coc_lineage_valid,
        generation_valid=lineage.generation_valid,
        fork_detected=lineage.fork_detected,
        cycle_detected=lineage.cycle_detected,
        active_tip_poo_digest=lineage.active_tip_digest if lineage.lineage_valid else None,
        active_tip_state_digest=state_digest(active_state) if active_state else None,
        lineage_issue_count=len(lineage.issues),
        reasons=list(reasons),
        transition=transition,
        candidate_state_digest=candidate_digest,
        digest=_decision_digest(
            operation=operation,
            lineage=lineage,
            base_digest=base_digest,
            active_state=active_state,
            candidate_state_digest=candidate_digest,
        ),
        technical_state_committed=False,
        conflict_winner_selected=False,
        lineage_auto_resolved=False,
        legal_title_changed=False,
        live_value_moved=False,
        external_transfer_executed=False,
        claims_boundary=_boundary(),
    )


def evaluate_governed_transfer_transition(
    states: Iterable[TechnicalOwnershipState],
    transfer: TransferEvidence,
    recipient_coc: COCEvidence,
) -> GovernedStateTransitionDecision:
    records = list(states)
    lineage = evaluate_state_lineage(records)
    active = _active_state(records, lineage)
    transfer_decision = evaluate_transfer(transfer)
    coc_decision = evaluate_coc(recipient_coc)
    base_ready = transfer_decision.transfer_ready and coc_decision.coc_valid
    reasons: list[str] = []

    if not lineage.lineage_valid:
        reasons.extend(f"state lineage: {issue}" for issue in lineage.issues)
        return _result(
            operation="TRANSFER_SUPERSESSION",
            status="STATE_LINEAGE_CONFLICT_BLOCKED",
            ready=False,
            base_evidence_ready=base_ready,
            lineage=lineage,
            active_state=None,
            reasons=reasons,
            transition=None,
            base_digest=transfer_decision.digest + ":" + coc_decision.digest,
        )

    if active is None:
        reasons.append("state lineage active tip could not be resolved uniquely")
        return _result(
            operation="TRANSFER_SUPERSESSION",
            status="STATE_LINEAGE_ACTIVE_TIP_UNRESOLVED",
            ready=False,
            base_evidence_ready=base_ready,
            lineage=lineage,
            active_state=None,
            reasons=reasons,
            transition=None,
            base_digest=transfer_decision.digest + ":" + coc_decision.digest,
        )

    transition = prepare_transfer_transition(active, transfer, recipient_coc)
    reasons.extend(transition.reasons)
    ready = transition.ready and not reasons
    status = "STATE_TRANSFER_READY_WITH_LINEAGE_GUARD" if ready else "STATE_TRANSFER_GOVERNANCE_BLOCKED"
    return _result(
        operation="TRANSFER_SUPERSESSION",
        status=status,
        ready=ready,
        base_evidence_ready=base_ready,
        lineage=lineage,
        active_state=active,
        reasons=reasons,
        transition=transition,
        base_digest=transfer_decision.digest + ":" + coc_decision.digest,
    )


def evaluate_governed_recovery_transition(
    states: Iterable[TechnicalOwnershipState],
    recovery: RecoveryEvidence,
    replacement_coc: COCEvidence,
) -> GovernedStateTransitionDecision:
    records = list(states)
    lineage = evaluate_state_lineage(records)
    active = _active_state(records, lineage)
    recovery_decision = evaluate_recovery(recovery)
    coc_decision = evaluate_coc(replacement_coc)
    base_ready = recovery_decision.recovery_ready and coc_decision.coc_valid
    reasons: list[str] = []

    if not lineage.lineage_valid:
        reasons.extend(f"state lineage: {issue}" for issue in lineage.issues)
        return _result(
            operation="RECOVERY_SUPERSESSION",
            status="STATE_LINEAGE_CONFLICT_BLOCKED",
            ready=False,
            base_evidence_ready=base_ready,
            lineage=lineage,
            active_state=None,
            reasons=reasons,
            transition=None,
            base_digest=recovery_decision.digest + ":" + coc_decision.digest,
        )

    if active is None:
        reasons.append("state lineage active tip could not be resolved uniquely")
        return _result(
            operation="RECOVERY_SUPERSESSION",
            status="STATE_LINEAGE_ACTIVE_TIP_UNRESOLVED",
            ready=False,
            base_evidence_ready=base_ready,
            lineage=lineage,
            active_state=None,
            reasons=reasons,
            transition=None,
            base_digest=recovery_decision.digest + ":" + coc_decision.digest,
        )

    transition = prepare_recovery_transition(active, recovery, replacement_coc)
    reasons.extend(transition.reasons)
    ready = transition.ready and not reasons
    status = "STATE_RECOVERY_READY_WITH_LINEAGE_GUARD" if ready else "STATE_RECOVERY_GOVERNANCE_BLOCKED"
    return _result(
        operation="RECOVERY_SUPERSESSION",
        status=status,
        ready=ready,
        base_evidence_ready=base_ready,
        lineage=lineage,
        active_state=active,
        reasons=reasons,
        transition=transition,
        base_digest=recovery_decision.digest + ":" + coc_decision.digest,
    )
