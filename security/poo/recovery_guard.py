"""Worldshepherd Proof of Ownership same-owner recovery guard.

Recovery handles lost/compromised control for the same ownership claimant. It is
separate from ordinary transfer and cannot silently change ownership, rotate keys,
move value, or adjudicate legal title.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Optional

from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership

RECOVERY_SCHEMA = "WS-POO-RECOVERY-V3"
_ALLOWED_REASONS = {
    "LOST_CONTROL",
    "COMPROMISED_CONTROL",
    "CUSTODY_FAILURE",
    "TECHNICAL_RECORD_CORRECTION",
}


@dataclass(frozen=True)
class RecoveryEvidence:
    asset_id: str
    prior_poo_digest: str
    claimant_id: str
    recovery_reason: str
    title_reference: str
    new_control_key_fingerprint: str
    recovery_work_reference: str
    recovery_concept_reference: str
    recovery_coc_reference: str
    recovery_stake_reference: str
    recovery_request_reference: str
    issued_at: str
    expires_at: str

    prior_poo_valid: bool = False
    asset_continuity_verified: bool = False
    claimant_continuity_verified: bool = False
    claimant_identity_reverified: bool = False
    title_or_provenance_reverified: bool = False
    compromise_or_loss_evidence_bound: bool = False
    recovery_pow_verified: bool = False
    recovery_poc_concept_verified: bool = False
    alternate_coc_verified: bool = False
    recovery_pos_bond_verified: bool = False
    multisource_or_quorum_verified: bool = False
    freshness_verified: bool = False
    recovery_not_revoked: bool = True
    active_dispute: bool = False
    dispute_resolution_verified: bool = False
    human_approval_verified: bool = False
    external_title_reference_verified: bool = False


@dataclass(frozen=True)
class RecoveryDecision:
    schema: str
    status: str
    recovery_ready: bool
    prior_control_revocation_ready: bool
    ownership_restored: bool
    control_rotated: bool
    transfer_executed: bool
    live_value_authorized: bool
    legal_title_changed: bool
    missing_predicates: List[str]
    digest: str
    claims_boundary: Dict[str, bool]


def canonical_recovery_payload(evidence: RecoveryEvidence) -> Dict[str, object]:
    return {
        "schema": RECOVERY_SCHEMA,
        "asset_id": evidence.asset_id,
        "prior_poo_digest": evidence.prior_poo_digest,
        "claimant_id": evidence.claimant_id,
        "recovery_reason": evidence.recovery_reason,
        "title_reference": evidence.title_reference,
        "new_control_key_fingerprint": evidence.new_control_key_fingerprint,
        "recovery_work_reference": evidence.recovery_work_reference,
        "recovery_concept_reference": evidence.recovery_concept_reference,
        "recovery_coc_reference": evidence.recovery_coc_reference,
        "recovery_stake_reference": evidence.recovery_stake_reference,
        "recovery_request_reference": evidence.recovery_request_reference,
        "issued_at": evidence.issued_at,
        "expires_at": evidence.expires_at,
    }


def recovery_digest(evidence: RecoveryEvidence) -> str:
    raw = json.dumps(
        canonical_recovery_payload(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _missing_predicates(evidence: RecoveryEvidence) -> List[str]:
    required = {
        "prior_poo_valid": "prior PoO not valid",
        "asset_continuity_verified": "asset continuity not verified",
        "claimant_continuity_verified": "claimant continuity not verified",
        "claimant_identity_reverified": "claimant identity not reverified",
        "title_or_provenance_reverified": "title/provenance not reverified",
        "compromise_or_loss_evidence_bound": "loss/compromise evidence not bound",
        "recovery_pow_verified": "recovery PoW not verified",
        "recovery_poc_concept_verified": "recovery PoC concept not verified",
        "alternate_coc_verified": "alternate COC not verified",
        "recovery_pos_bond_verified": "recovery PoS bond not verified",
        "multisource_or_quorum_verified": "multisource/quorum evidence not verified",
        "freshness_verified": "recovery freshness not verified",
        "recovery_not_revoked": "recovery revoked",
        "human_approval_verified": "human approval not verified",
    }
    missing = [reason for field, reason in required.items() if not getattr(evidence, field)]
    if not evidence.recovery_coc_reference:
        missing.append("recovery COC reference must be non-empty")
    if evidence.recovery_reason not in _ALLOWED_REASONS:
        missing.append("recovery reason not allowed")
    if evidence.active_dispute and not evidence.dispute_resolution_verified:
        missing.append("active dispute not resolved")
    return missing


def evaluate_recovery(evidence: RecoveryEvidence) -> RecoveryDecision:
    missing = _missing_predicates(evidence)
    ready = not missing

    if evidence.active_dispute and not evidence.dispute_resolution_verified:
        status = "RECOVERY_DISPUTE_REVIEW_REQUIRED"
    elif ready:
        status = "READY_FOR_GOVERNED_RECOVERY_SUPERSESSION"
    else:
        status = "INSUFFICIENT_RECOVERY_EVIDENCE"

    return RecoveryDecision(
        schema=RECOVERY_SCHEMA,
        status=status,
        recovery_ready=ready,
        prior_control_revocation_ready=ready,
        ownership_restored=False,
        control_rotated=False,
        transfer_executed=False,
        live_value_authorized=False,
        legal_title_changed=False,
        missing_predicates=missing,
        digest=recovery_digest(evidence),
        claims_boundary={
            "automatic_key_rotation": False,
            "automatic_prior_control_revocation": False,
            "ownership_change": False,
            "transfer_execution": False,
            "live_value_movement": False,
            "legal_title_adjudication": False,
            "government_registry_authority": False,
            "external_validation_established": False,
        },
    )


def derive_recovery_ownership_candidate(
    recovery: RecoveryEvidence,
    *,
    title_reference: Optional[str] = None,
) -> OwnershipEvidence:
    decision = evaluate_recovery(recovery)
    if not decision.recovery_ready:
        raise ValueError("recovery is not ready for governed supersession")

    candidate = OwnershipEvidence(
        asset_id=recovery.asset_id,
        claimant_id=recovery.claimant_id,
        title_reference=title_reference or recovery.title_reference,
        control_key_fingerprint=recovery.new_control_key_fingerprint,
        work_reference=recovery.recovery_work_reference,
        concept_reference=recovery.recovery_concept_reference,
        coc_reference=recovery.recovery_coc_reference,
        stake_reference=recovery.recovery_stake_reference,
        issued_at=recovery.issued_at,
        expires_at=recovery.expires_at,
        previous_poo_digest=recovery.prior_poo_digest,
        asset_fingerprint_bound=recovery.asset_continuity_verified,
        claimant_identity_bound=recovery.claimant_identity_reverified,
        title_or_provenance_bound=recovery.title_or_provenance_reverified,
        pow_verified=recovery.recovery_pow_verified,
        poc_concept_verified=recovery.recovery_poc_concept_verified,
        coc_verified=recovery.alternate_coc_verified,
        pos_bond_verified=recovery.recovery_pos_bond_verified,
        freshness_verified=recovery.freshness_verified,
        not_revoked=recovery.recovery_not_revoked,
        external_title_reference_verified=recovery.external_title_reference_verified,
    )
    if not evaluate_ownership(candidate).poo_valid:
        raise ValueError("derived recovery ownership candidate is not PoO-valid")
    return candidate


def recovery_record(evidence: RecoveryEvidence) -> Dict[str, object]:
    return {
        "evidence": asdict(evidence),
        "decision": asdict(evaluate_recovery(evidence)),
    }
