"""Worldshepherd Control/Custody Verification (COC) guard.

COC is a first-class evidence object used by Proof of Ownership (PoO). It verifies
technical control/custody evidence for an asset-bound control surface and may carry
a point-of-custody reference. It does not adjudicate legal custody, legal title,
regulatory status, or transfer authority.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Optional

COC_SCHEMA = "WS-POO-COC-V1"


@dataclass(frozen=True)
class COCEvidence:
    asset_id: str
    claimant_id: str
    control_key_fingerprint: str
    custody_reference: str
    custody_point_reference: str
    challenge_reference: str
    observed_at: str
    expires_at: str
    previous_coc_digest: Optional[str] = None

    asset_binding_verified: bool = False
    claimant_binding_verified: bool = False
    custody_or_control_verified: bool = False
    challenge_response_verified: bool = False
    custody_chain_verified: bool = False
    freshness_verified: bool = False
    not_revoked: bool = True


@dataclass(frozen=True)
class COCDecision:
    schema: str
    status: str
    coc_valid: bool
    technical_control_custody_attested: bool
    legal_custody_established: bool
    missing_predicates: List[str]
    digest: str
    claims_boundary: Dict[str, bool]


_REQUIRED = {
    "asset_binding_verified": "COC asset binding not verified",
    "claimant_binding_verified": "COC claimant binding not verified",
    "custody_or_control_verified": "COC control/custody not verified",
    "challenge_response_verified": "COC challenge response not verified",
    "custody_chain_verified": "COC custody chain not verified",
    "freshness_verified": "COC freshness not verified",
    "not_revoked": "COC revoked",
}


def canonical_coc_payload(evidence: COCEvidence) -> Dict[str, object]:
    return {
        "schema": COC_SCHEMA,
        "asset_id": evidence.asset_id,
        "claimant_id": evidence.claimant_id,
        "control_key_fingerprint": evidence.control_key_fingerprint,
        "custody_reference": evidence.custody_reference,
        "custody_point_reference": evidence.custody_point_reference,
        "challenge_reference": evidence.challenge_reference,
        "observed_at": evidence.observed_at,
        "expires_at": evidence.expires_at,
        "previous_coc_digest": evidence.previous_coc_digest,
    }


def coc_digest(evidence: COCEvidence) -> str:
    raw = json.dumps(
        canonical_coc_payload(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_coc(evidence: COCEvidence) -> COCDecision:
    missing = [reason for field, reason in _REQUIRED.items() if not getattr(evidence, field)]
    for field in (
        "asset_id",
        "claimant_id",
        "control_key_fingerprint",
        "custody_reference",
        "custody_point_reference",
        "challenge_reference",
        "observed_at",
        "expires_at",
    ):
        if not getattr(evidence, field):
            missing.append(f"COC {field} must be non-empty")

    valid = not missing
    return COCDecision(
        schema=COC_SCHEMA,
        status="TECHNICAL_COC_ATTESTATION" if valid else "INSUFFICIENT_COC_EVIDENCE",
        coc_valid=valid,
        technical_control_custody_attested=valid,
        legal_custody_established=False,
        missing_predicates=missing,
        digest=coc_digest(evidence),
        claims_boundary={
            "legal_custody_adjudicated": False,
            "legal_title_adjudicated": False,
            "government_registry_authority": False,
            "transfer_execution_authority": False,
            "live_value_authority": False,
            "external_validation_established": False,
        },
    )


def coc_record(evidence: COCEvidence) -> Dict[str, object]:
    return {
        "evidence": asdict(evidence),
        "decision": asdict(evaluate_coc(evidence)),
    }
