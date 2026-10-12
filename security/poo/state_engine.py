"""Deterministic technical-state engine for Worldshepherd Proof of Ownership.

The engine derives candidate technical ownership states from already governed PoO,
transfer, recovery, and COC evidence. It never changes legal title, moves value,
rotates credentials, or executes an external transfer. Its output is an immutable
candidate ledger state suitable for SARA/ECHO governance and audit custody.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.lineage_guard import LineageNode, evaluate_lineage
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.recovery_guard import (
    RecoveryEvidence,
    derive_recovery_ownership_candidate,
    evaluate_recovery,
)
from security.poo.transfer_guard import (
    TransferEvidence,
    derive_recipient_ownership_evidence,
    evaluate_transfer,
)

STATE_SCHEMA = "WS-POO-TECHNICAL-STATE-V1"
STATE_LINEAGE_SCHEMA = "WS-POO-STATE-LINEAGE-V1"


@dataclass(frozen=True)
class TechnicalOwnershipState:
    schema: str
    asset_id: str
    claimant_id: str
    active_poo_digest: str
    active_coc_digest: str
    control_key_fingerprint: str
    title_reference: str
    generation: int
    source_event_type: str
    previous_poo_digest: Optional[str]
    previous_coc_digest: Optional[str]
    legal_title_established: bool = False
    live_value_authorized: bool = False
    external_transfer_executed: bool = False


@dataclass(frozen=True)
class StateTransitionDecision:
    schema: str
    operation: str
    status: str
    ready: bool
    reasons: List[str]
    current_state_digest: Optional[str]
    candidate_state: Optional[TechnicalOwnershipState]
    candidate_state_digest: Optional[str]
    technical_state_committed: bool
    legal_title_changed: bool
    live_value_moved: bool
    external_transfer_executed: bool
    claims_boundary: Dict[str, bool]


@dataclass(frozen=True)
class StateLineageDecision:
    schema: str
    status: str
    lineage_valid: bool
    poo_lineage_valid: bool
    coc_lineage_valid: bool
    generation_valid: bool
    fork_detected: bool
    cycle_detected: bool
    active_tip_digest: Optional[str]
    issues: List[str]
    digest: str
    legal_title_established: bool
    claims_boundary: Dict[str, bool]


def state_digest(state: TechnicalOwnershipState) -> str:
    raw = json.dumps(asdict(state), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def state_lineage_digest(states: Iterable[TechnicalOwnershipState]) -> str:
    canonical = [asdict(state) for state in states]
    canonical.sort(key=lambda item: (int(item["generation"]), str(item["active_poo_digest"])))
    raw = json.dumps(
        {"schema": STATE_LINEAGE_SCHEMA, "states": canonical},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _claims_boundary() -> Dict[str, bool]:
    return {
        "legal_title_adjudication": False,
        "government_registry_authority": False,
        "credential_rotation_authority": False,
        "live_value_movement": False,
        "external_transfer_execution": False,
        "external_validation_established": False,
    }


def _validate_coc_binding(
    coc: COCEvidence,
    *,
    asset_id: str,
    claimant_id: str,
    control_key_fingerprint: str,
    expected_coc_reference: str,
    expected_previous_coc_digest: Optional[str],
) -> List[str]:
    issues: list[str] = []
    decision = evaluate_coc(coc)
    if not decision.coc_valid:
        issues.extend(decision.missing_predicates or ["COC not valid"])
    if decision.digest != expected_coc_reference:
        issues.append("COC digest does not match semantic COC reference")
    if coc.asset_id != asset_id:
        issues.append("COC asset does not match ownership asset")
    if coc.claimant_id != claimant_id:
        issues.append("COC claimant does not match ownership claimant")
    if coc.control_key_fingerprint != control_key_fingerprint:
        issues.append("COC control key does not match ownership control key")
    if coc.previous_coc_digest != expected_previous_coc_digest:
        issues.append("COC predecessor does not match active COC lineage")
    return issues


def bootstrap_technical_state(
    ownership: OwnershipEvidence,
    coc: COCEvidence,
) -> StateTransitionDecision:
    reasons: list[str] = []
    decision = evaluate_ownership(ownership)
    if not decision.poo_valid:
        reasons.extend(decision.missing_predicates or ["PoO not valid"])
    if ownership.previous_poo_digest is not None:
        reasons.append("bootstrap PoO must be genesis with no previous PoO")
    reasons.extend(
        _validate_coc_binding(
            coc,
            asset_id=ownership.asset_id,
            claimant_id=ownership.claimant_id,
            control_key_fingerprint=ownership.control_key_fingerprint,
            expected_coc_reference=ownership.coc_reference,
            expected_previous_coc_digest=None,
        )
    )

    candidate = None
    if not reasons:
        coc_decision = evaluate_coc(coc)
        candidate = TechnicalOwnershipState(
            schema=STATE_SCHEMA,
            asset_id=ownership.asset_id,
            claimant_id=ownership.claimant_id,
            active_poo_digest=decision.digest,
            active_coc_digest=coc_decision.digest,
            control_key_fingerprint=ownership.control_key_fingerprint,
            title_reference=ownership.title_reference,
            generation=0,
            source_event_type="CLAIM",
            previous_poo_digest=None,
            previous_coc_digest=None,
        )
    return _transition_decision("BOOTSTRAP", reasons, None, candidate)


def prepare_transfer_transition(
    current: TechnicalOwnershipState,
    transfer: TransferEvidence,
    recipient_coc: COCEvidence,
) -> StateTransitionDecision:
    reasons: list[str] = []
    decision = evaluate_transfer(transfer)
    if not decision.transfer_ready:
        reasons.extend(decision.missing_predicates or ["transfer not ready"])
    if current.asset_id != transfer.asset_id:
        reasons.append("transfer asset does not match current technical state")
    if current.claimant_id != transfer.current_owner_id:
        reasons.append("transfer current owner does not match active technical claimant")
    if current.active_poo_digest != transfer.prior_poo_digest:
        reasons.append("transfer predecessor does not match active PoO")

    reasons.extend(
        _validate_coc_binding(
            recipient_coc,
            asset_id=transfer.asset_id,
            claimant_id=transfer.recipient_id,
            control_key_fingerprint=transfer.recipient_control_key_fingerprint,
            expected_coc_reference=transfer.recipient_coc_reference,
            expected_previous_coc_digest=current.active_coc_digest,
        )
    )

    candidate_state = None
    if not reasons:
        ownership = derive_recipient_ownership_evidence(transfer)
        ownership_decision = evaluate_ownership(ownership)
        coc_decision = evaluate_coc(recipient_coc)
        candidate_state = TechnicalOwnershipState(
            schema=STATE_SCHEMA,
            asset_id=current.asset_id,
            claimant_id=ownership.claimant_id,
            active_poo_digest=ownership_decision.digest,
            active_coc_digest=coc_decision.digest,
            control_key_fingerprint=ownership.control_key_fingerprint,
            title_reference=ownership.title_reference,
            generation=current.generation + 1,
            source_event_type="TRANSFER",
            previous_poo_digest=current.active_poo_digest,
            previous_coc_digest=current.active_coc_digest,
        )
    return _transition_decision("TRANSFER_SUPERSESSION", reasons, current, candidate_state)


def prepare_recovery_transition(
    current: TechnicalOwnershipState,
    recovery: RecoveryEvidence,
    replacement_coc: COCEvidence,
) -> StateTransitionDecision:
    reasons: list[str] = []
    decision = evaluate_recovery(recovery)
    if not decision.recovery_ready:
        reasons.extend(decision.missing_predicates or ["recovery not ready"])
    if current.asset_id != recovery.asset_id:
        reasons.append("recovery asset does not match current technical state")
    if current.claimant_id != recovery.claimant_id:
        reasons.append("recovery claimant must match active technical claimant")
    if current.active_poo_digest != recovery.prior_poo_digest:
        reasons.append("recovery predecessor does not match active PoO")

    reasons.extend(
        _validate_coc_binding(
            replacement_coc,
            asset_id=recovery.asset_id,
            claimant_id=recovery.claimant_id,
            control_key_fingerprint=recovery.new_control_key_fingerprint,
            expected_coc_reference=recovery.recovery_coc_reference,
            expected_previous_coc_digest=current.active_coc_digest,
        )
    )

    candidate_state = None
    if not reasons:
        ownership = derive_recovery_ownership_candidate(recovery)
        ownership_decision = evaluate_ownership(ownership)
        coc_decision = evaluate_coc(replacement_coc)
        candidate_state = TechnicalOwnershipState(
            schema=STATE_SCHEMA,
            asset_id=current.asset_id,
            claimant_id=current.claimant_id,
            active_poo_digest=ownership_decision.digest,
            active_coc_digest=coc_decision.digest,
            control_key_fingerprint=ownership.control_key_fingerprint,
            title_reference=ownership.title_reference,
            generation=current.generation + 1,
            source_event_type="RECOVERY",
            previous_poo_digest=current.active_poo_digest,
            previous_coc_digest=current.active_coc_digest,
        )
    return _transition_decision("RECOVERY_SUPERSESSION", reasons, current, candidate_state)


def _transition_decision(
    operation: str,
    reasons: List[str],
    current: Optional[TechnicalOwnershipState],
    candidate: Optional[TechnicalOwnershipState],
) -> StateTransitionDecision:
    ready = not reasons and candidate is not None
    ready_status = (
        "TECHNICAL_STATE_BOOTSTRAP_READY"
        if operation == "BOOTSTRAP"
        else "TECHNICAL_STATE_SUPERSESSION_READY"
    )
    return StateTransitionDecision(
        schema=STATE_SCHEMA,
        operation=operation,
        status=ready_status if ready else "TECHNICAL_STATE_TRANSITION_BLOCKED",
        ready=ready,
        reasons=list(reasons),
        current_state_digest=state_digest(current) if current is not None else None,
        candidate_state=candidate,
        candidate_state_digest=state_digest(candidate) if candidate is not None else None,
        technical_state_committed=False,
        legal_title_changed=False,
        live_value_moved=False,
        external_transfer_executed=False,
        claims_boundary=_claims_boundary(),
    )


def evaluate_state_lineage(states: Iterable[TechnicalOwnershipState]) -> StateLineageDecision:
    records = list(states)
    issues: list[str] = []

    poo_children = {state.previous_poo_digest for state in records if state.previous_poo_digest}
    nodes = [
        LineageNode(
            poo_digest=state.active_poo_digest,
            asset_id=state.asset_id,
            claimant_id=state.claimant_id,
            previous_poo_digest=state.previous_poo_digest,
            event_type=state.source_event_type,
            technical_poo_valid=True,
            superseded=state.active_poo_digest in poo_children,
            revoked=False,
        )
        for state in records
    ]
    poo_decision = evaluate_lineage(nodes)
    if not poo_decision.lineage_valid:
        issues.extend(f"PoO: {issue}" for issue in poo_decision.issues)

    by_poo = {state.active_poo_digest: state for state in records}
    coc_digests = [state.active_coc_digest for state in records]
    coc_valid = True
    if len(set(coc_digests)) != len(coc_digests):
        coc_valid = False
        issues.append("COC: duplicate active COC digest")

    for state in records:
        if state.previous_poo_digest is None:
            if state.previous_coc_digest is not None:
                coc_valid = False
                issues.append("COC: genesis technical state must have no previous COC")
            continue
        parent = by_poo.get(state.previous_poo_digest)
        if parent is None:
            coc_valid = False
            issues.append(f"COC: predecessor PoO missing for generation {state.generation}")
            continue
        if state.previous_coc_digest != parent.active_coc_digest:
            coc_valid = False
            issues.append(f"COC: predecessor mismatch at generation {state.generation}")

    actual_generations = sorted(state.generation for state in records)
    expected_generations = list(range(len(records)))
    generation_valid = actual_generations == expected_generations
    if not generation_valid:
        issues.append("state generations must be contiguous from zero")

    schemas_valid = all(state.schema == STATE_SCHEMA for state in records)
    if not schemas_valid:
        issues.append("unsupported technical ownership state schema")

    valid = poo_decision.lineage_valid and coc_valid and generation_valid and schemas_valid and not issues
    active_tip = poo_decision.active_tip_digest if valid else None
    return StateLineageDecision(
        schema=STATE_LINEAGE_SCHEMA,
        status="STATE_LINEAGE_INTERNALLY_CONSISTENT" if valid else "STATE_LINEAGE_REVIEW_REQUIRED",
        lineage_valid=valid,
        poo_lineage_valid=poo_decision.lineage_valid,
        coc_lineage_valid=coc_valid,
        generation_valid=generation_valid,
        fork_detected=poo_decision.fork_detected,
        cycle_detected=poo_decision.cycle_detected,
        active_tip_digest=active_tip,
        issues=issues,
        digest=state_lineage_digest(records),
        legal_title_established=False,
        claims_boundary=_claims_boundary(),
    )
