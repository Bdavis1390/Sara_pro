"""Worldshepherd Proof of Ownership (PoO) guard.

PoO composes independent predicates:
- title/provenance binding
- PoW: bounded claim-specific work evidence
- PoC: bounded Proof of Concept showing the claimed ownership mechanism works
- COC: Control/Custody verification over the asset-bound control surface
- PoS: slashable/bonded economic commitment

This module produces a technical ownership attestation only. It never adjudicates
legal title, regulatory status, or transfer validity by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Optional


POO_SCHEMA = "WS-POO-V2"


@dataclass(frozen=True)
class OwnershipEvidence:
    asset_id: str
    claimant_id: str
    title_reference: str
    control_key_fingerprint: str
    work_reference: str
    concept_reference: str
    stake_reference: str
    issued_at: str
    expires_at: str
    previous_poo_digest: Optional[str] = None

    asset_fingerprint_bound: bool = False
    claimant_identity_bound: bool = False
    title_or_provenance_bound: bool = False
    pow_verified: bool = False
    poc_concept_verified: bool = False
    coc_verified: bool = False
    pos_bond_verified: bool = False
    freshness_verified: bool = False
    not_revoked: bool = True
    external_title_reference_verified: bool = False


@dataclass(frozen=True)
class OwnershipDecision:
    schema: str
    status: str
    poo_valid: bool
    technical_ownership_attested: bool
    legal_ownership_established: bool
    missing_predicates: List[str]
    digest: str
    claims_boundary: Dict[str, bool]


_REQUIRED = {
    "asset_fingerprint_bound": "asset fingerprint not bound",
    "claimant_identity_bound": "claimant identity not bound",
    "title_or_provenance_bound": "title/provenance not bound",
    "pow_verified": "PoW not verified",
    "poc_concept_verified": "PoC concept not verified",
    "coc_verified": "COC not verified",
    "pos_bond_verified": "PoS bond not verified",
    "freshness_verified": "freshness not verified",
    "not_revoked": "claim revoked",
}


def canonical_claim_payload(evidence: OwnershipEvidence) -> Dict[str, object]:
    """Return deterministic semantic claim material for hashing/auditing."""
    return {
        "schema": POO_SCHEMA,
        "asset_id": evidence.asset_id,
        "claimant_id": evidence.claimant_id,
        "title_reference": evidence.title_reference,
        "control_key_fingerprint": evidence.control_key_fingerprint,
        "work_reference": evidence.work_reference,
        "concept_reference": evidence.concept_reference,
        "stake_reference": evidence.stake_reference,
        "issued_at": evidence.issued_at,
        "expires_at": evidence.expires_at,
        "previous_poo_digest": evidence.previous_poo_digest,
    }


def ownership_digest(evidence: OwnershipEvidence) -> str:
    raw = json.dumps(
        canonical_claim_payload(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_ownership(evidence: OwnershipEvidence) -> OwnershipDecision:
    """Evaluate a PoO claim with fail-closed AND semantics.

    No weighted score is used. A wealthy or compute-rich claimant cannot compensate
    for missing proof-of-concept, COC, provenance, freshness, or revocation checks.
    """
    missing = [reason for field, reason in _REQUIRED.items() if not getattr(evidence, field)]
    valid = not missing

    status = "TECHNICAL_OWNERSHIP_ATTESTATION" if valid else "INSUFFICIENT_OWNERSHIP_EVIDENCE"
    if valid and evidence.external_title_reference_verified:
        status = "TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE"

    return OwnershipDecision(
        schema=POO_SCHEMA,
        status=status,
        poo_valid=valid,
        technical_ownership_attested=valid,
        legal_ownership_established=False,
        missing_predicates=missing,
        digest=ownership_digest(evidence),
        claims_boundary={
            "legal_title_adjudicated": False,
            "government_registry_authority": False,
            "transfer_execution_authority": False,
            "live_value_authority": False,
            "external_validation_established": False,
        },
    )


def decision_record(evidence: OwnershipEvidence) -> Dict[str, object]:
    decision = evaluate_ownership(evidence)
    return {
        "evidence": asdict(evidence),
        "decision": asdict(decision),
    }
