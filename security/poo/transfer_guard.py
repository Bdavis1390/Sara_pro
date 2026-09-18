"""Worldshepherd Proof of Ownership transfer-readiness guard.

This module prepares a new technical ownership attestation linked to a prior PoO.
It does not execute transfers, move value, adjudicate title, or supersede records by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Optional

from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership

TRANSFER_SCHEMA = "WS-POO-TRANSFER-V3"


@dataclass(frozen=True)
class TransferEvidence:
    asset_id: str
    prior_poo_digest: str
    current_owner_id: str
    recipient_id: str
    title_transition_reference: str
    recipient_control_key_fingerprint: str
    recipient_work_reference: str
    recipient_concept_reference: str
    recipient_coc_reference: str
    recipient_stake_reference: str
    initiated_at: str
    expires_at: str

    prior_poo_valid: bool = False
    asset_continuity_verified: bool = False
    current_owner_authorized: bool = False
    recipient_identity_bound: bool = False
    recipient_poc_concept_verified: bool = False
    recipient_coc_verified: bool = False
    recipient_pow_verified: bool = False
    recipient_pos_bond_verified: bool = False
    title_or_provenance_transition_bound: bool = False
    freshness_verified: bool = False
    no_active_dispute: bool = True
    transfer_not_revoked: bool = True
    human_approval_verified: bool = False
    external_title_transition_verified: bool = False


@dataclass(frozen=True)
class TransferDecision:
    schema: str
    status: str
    transfer_ready: bool
    supersession_ready: bool
    transfer_executed: bool
    live_value_authorized: bool
    legal_title_transferred: bool
    missing_predicates: List[str]
    digest: str
    claims_boundary: Dict[str, bool]


_REQUIRED = {
    "prior_poo_valid": "prior PoO not valid",
    "asset_continuity_verified": "asset continuity not verified",
    "current_owner_authorized": "current owner authorization not verified",
    "recipient_identity_bound": "recipient identity not bound",
    "recipient_poc_concept_verified": "recipient PoC concept not verified",
    "recipient_coc_verified": "recipient COC not verified",
    "recipient_pow_verified": "recipient PoW not verified",
    "recipient_pos_bond_verified": "recipient PoS bond not verified",
    "title_or_provenance_transition_bound": "title/provenance transition not bound",
    "freshness_verified": "transfer freshness not verified",
    "no_active_dispute": "active ownership dispute",
    "transfer_not_revoked": "transfer revoked",
    "human_approval_verified": "human approval not verified",
}


def canonical_transfer_payload(evidence: TransferEvidence) -> Dict[str, object]:
    return {
        "schema": TRANSFER_SCHEMA,
        "asset_id": evidence.asset_id,
        "prior_poo_digest": evidence.prior_poo_digest,
        "current_owner_id": evidence.current_owner_id,
        "recipient_id": evidence.recipient_id,
        "title_transition_reference": evidence.title_transition_reference,
        "recipient_control_key_fingerprint": evidence.recipient_control_key_fingerprint,
        "recipient_work_reference": evidence.recipient_work_reference,
        "recipient_concept_reference": evidence.recipient_concept_reference,
        "recipient_coc_reference": evidence.recipient_coc_reference,
        "recipient_stake_reference": evidence.recipient_stake_reference,
        "initiated_at": evidence.initiated_at,
        "expires_at": evidence.expires_at,
    }


def transfer_digest(evidence: TransferEvidence) -> str:
    raw = json.dumps(
        canonical_transfer_payload(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_transfer(evidence: TransferEvidence) -> TransferDecision:
    missing = [reason for field, reason in _REQUIRED.items() if not getattr(evidence, field)]
    if not evidence.recipient_coc_reference:
        missing.append("recipient COC reference must be non-empty")
    ready = not missing

    if not evidence.no_active_dispute:
        status = "TRANSFER_DISPUTED_BLOCKED"
    elif ready:
        status = "READY_FOR_GOVERNED_SUPERSESSION"
    else:
        status = "INSUFFICIENT_TRANSFER_EVIDENCE"

    return TransferDecision(
        schema=TRANSFER_SCHEMA,
        status=status,
        transfer_ready=ready,
        supersession_ready=ready,
        transfer_executed=False,
        live_value_authorized=False,
        legal_title_transferred=False,
        missing_predicates=missing,
        digest=transfer_digest(evidence),
        claims_boundary={
            "automatic_transfer_execution": False,
            "live_value_movement": False,
            "legal_title_adjudication": False,
            "government_registry_authority": False,
            "external_validation_established": False,
        },
    )


def derive_recipient_ownership_evidence(
    transfer: TransferEvidence,
    *,
    recipient_title_reference: Optional[str] = None,
) -> OwnershipEvidence:
    decision = evaluate_transfer(transfer)
    if not decision.transfer_ready:
        raise ValueError("transfer is not ready for governed supersession")

    candidate = OwnershipEvidence(
        asset_id=transfer.asset_id,
        claimant_id=transfer.recipient_id,
        title_reference=recipient_title_reference or transfer.title_transition_reference,
        control_key_fingerprint=transfer.recipient_control_key_fingerprint,
        work_reference=transfer.recipient_work_reference,
        concept_reference=transfer.recipient_concept_reference,
        coc_reference=transfer.recipient_coc_reference,
        stake_reference=transfer.recipient_stake_reference,
        issued_at=transfer.initiated_at,
        expires_at=transfer.expires_at,
        previous_poo_digest=transfer.prior_poo_digest,
        asset_fingerprint_bound=True,
        claimant_identity_bound=transfer.recipient_identity_bound,
        title_or_provenance_bound=transfer.title_or_provenance_transition_bound,
        pow_verified=transfer.recipient_pow_verified,
        poc_concept_verified=transfer.recipient_poc_concept_verified,
        coc_verified=transfer.recipient_coc_verified,
        pos_bond_verified=transfer.recipient_pos_bond_verified,
        freshness_verified=transfer.freshness_verified,
        not_revoked=transfer.transfer_not_revoked,
        external_title_reference_verified=transfer.external_title_transition_verified,
    )

    if not evaluate_ownership(candidate).poo_valid:
        raise ValueError("derived recipient ownership candidate is not PoO-valid")
    return candidate


def transfer_record(evidence: TransferEvidence) -> Dict[str, object]:
    return {
        "evidence": asdict(evidence),
        "decision": asdict(evaluate_transfer(evidence)),
    }
