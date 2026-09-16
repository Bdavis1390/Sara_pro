"""Conservative VC 2.0 mapping proposal for Worldshepherd PoO/COC.

This module deliberately does NOT claim W3C conformance and does not mint, sign,
issue, revoke, or present a Verifiable Credential. It separates fields that map
cleanly to the VC 2.0 core data model from Worldshepherd extension candidates that
require standards/community review.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Optional

from security.poo.coc_guard import COCEvidence, coc_digest, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership, ownership_digest

MAPPING_SCHEMA = "WS-POO-VC20-MAPPING-DRAFT-V1"
VC20_CONTEXT = "https://www.w3.org/ns/credentials/v2"


@dataclass(frozen=True)
class VCMappingDecision:
    schema: str
    status: str
    mapping_ready_for_external_review: bool
    mapping_digest: str
    vc20_core_projection: Dict[str, object]
    extension_candidates: Dict[str, object]
    unresolved_mapping_questions: List[str]
    vc20_conformance_established: bool
    did_conformance_established: bool
    openid4vp_conformance_established: bool
    credential_issued: bool
    credential_signed: bool
    issuer_authority_established: bool
    legal_ownership_established: bool
    claims_boundary: Dict[str, bool]


def _canonical_mapping_payload(*, ownership: OwnershipEvidence, coc: COCEvidence, issuer_id: str, credential_id: Optional[str]) -> Dict[str, object]:
    return {
        "schema": MAPPING_SCHEMA,
        "issuer_id": issuer_id,
        "credential_id": credential_id,
        "ownership_digest": ownership_digest(ownership),
        "coc_digest": coc_digest(coc),
        "asset_id": ownership.asset_id,
        "claimant_id": ownership.claimant_id,
        "valid_from": ownership.issued_at,
        "valid_until": ownership.expires_at,
    }


def _mapping_digest(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def project_vc20_mapping(ownership: OwnershipEvidence, coc: COCEvidence, *, issuer_id: str, credential_id: Optional[str] = None) -> VCMappingDecision:
    """Build a review-only VC 2.0 mapping proposal with fail-closed inputs."""
    reasons: List[str] = []
    ownership_decision = evaluate_ownership(ownership)
    coc_decision = evaluate_coc(coc)

    if not ownership_decision.poo_valid:
        reasons.append("PoO evidence is not internally valid")
    if not coc_decision.coc_valid:
        reasons.append("COC evidence is not internally valid")
    actual_coc_digest = coc_digest(coc)
    if ownership.coc_reference != actual_coc_digest:
        reasons.append("PoO COC reference does not match supplied COC digest")
    if ownership.asset_id != coc.asset_id:
        reasons.append("PoO/COC asset mismatch")
    if ownership.claimant_id != coc.claimant_id:
        reasons.append("PoO/COC claimant mismatch")
    if ownership.control_key_fingerprint != coc.control_key_fingerprint:
        reasons.append("PoO/COC control-key mismatch")
    if not issuer_id:
        reasons.append("issuer_id must be non-empty")

    mapping_ready = not reasons
    core: Dict[str, object] = {
        "@context": [VC20_CONTEXT],
        "type": ["VerifiableCredential"],
        "issuer": issuer_id,
        "validFrom": ownership.issued_at,
        "validUntil": ownership.expires_at,
        "credentialSubject": {"id": ownership.claimant_id},
    }
    if credential_id:
        core["id"] = credential_id

    extensions = {
        "assetId": ownership.asset_id,
        "pooDigest": ownership_digest(ownership),
        "cocDigest": actual_coc_digest,
        "previousPooDigest": ownership.previous_poo_digest,
        "previousCocDigest": coc.previous_coc_digest,
        "custodyEvidenceReference": coc.custody_reference,
        "custodyPointReference": coc.custody_point_reference,
        "challengeEvidenceReference": coc.challenge_reference,
        "technicalOwnershipOnly": True,
        "legalOwnershipEstablished": False,
    }

    payload = _canonical_mapping_payload(ownership=ownership, coc=coc, issuer_id=issuer_id, credential_id=credential_id)
    unresolved = [
        "select or define standards-reviewed vocabulary terms for PoO/COC extensions",
        "determine whether COC evidence belongs in credential claims, evidence metadata, or a referenced credential",
        "define credential status/revocation mapping without inventing a status endpoint",
        "define DID/controller verification-method mapping for the control-key fingerprint",
        "define OpenID4VP presentation/challenge mapping and verifier nonce semantics",
        "select an approved integrity mechanism and issuer trust policy before issuance",
        "complete privacy/minimization review before exposing custody references",
    ]
    unresolved.extend(reasons)

    return VCMappingDecision(
        schema=MAPPING_SCHEMA,
        status="READY_FOR_STANDARDS_REVIEW" if mapping_ready else "BLOCKED_MAPPING_INPUT",
        mapping_ready_for_external_review=mapping_ready,
        mapping_digest=_mapping_digest(payload),
        vc20_core_projection=core,
        extension_candidates=extensions,
        unresolved_mapping_questions=unresolved,
        vc20_conformance_established=False,
        did_conformance_established=False,
        openid4vp_conformance_established=False,
        credential_issued=False,
        credential_signed=False,
        issuer_authority_established=False,
        legal_ownership_established=False,
        claims_boundary={
            "w3c_conformance_claimed": False,
            "openid_conformance_claimed": False,
            "custom_vocabulary_standardized": False,
            "proof_generated": False,
            "credential_status_generated": False,
            "legal_title_adjudicated": False,
            "external_validation_established": False,
        },
    )


def mapping_record(decision: VCMappingDecision) -> Dict[str, object]:
    return asdict(decision)
