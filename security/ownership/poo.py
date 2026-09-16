"""Worldshepherd Proof of Ownership (PoO) core.

PoO intentionally combines four independent evidence gates:

1. CONTROL: evidence that the claimant controls the asserted key/credential.
2. PROVENANCE: evidence linking that claimant/key to the asset record.
3. WORK: a bounded proof-of-work challenge used only as anti-spam/replay cost.
4. STAKE: a bonded proof-of-stake attestation used only as accountability.

PoW and PoS are supporting evidence. Neither establishes ownership by itself.
This module does not establish legal title, regulatory ownership, beneficial
ownership, or court-recognized property rights.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Optional


POO_SCHEMA = "WS-POO-V1"


def _canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def leading_zero_bits(digest: bytes) -> int:
    count = 0
    for byte in digest:
        if byte == 0:
            count += 8
            continue
        count += 8 - byte.bit_length()
        break
    return count


def ownership_claim_digest(*, asset_id: str, claimant_id: str, key_fingerprint: str, provenance_ref: str) -> str:
    payload = {
        "schema": POO_SCHEMA,
        "asset_id": asset_id,
        "claimant_id": claimant_id,
        "key_fingerprint": key_fingerprint,
        "provenance_ref": provenance_ref,
    }
    return sha256(_canonical_json(payload)).hexdigest()


def verify_work(*, claim_digest: str, nonce: int, difficulty_bits: int) -> bool:
    """Verify a bounded PoW challenge for an ownership claim.

    This is an anti-spam/replay cost only. It does not prove asset ownership.
    """
    if nonce < 0 or difficulty_bits < 0 or difficulty_bits > 32:
        return False
    material = f"{POO_SCHEMA}|{claim_digest}|{nonce}".encode("utf-8")
    return leading_zero_bits(sha256(material).digest()) >= difficulty_bits


@dataclass(frozen=True)
class OwnershipEvidence:
    asset_id: str
    claimant_id: str
    key_fingerprint: str
    provenance_ref: str

    control_challenge_ref: str
    control_verified: bool

    work_nonce: int
    work_difficulty_bits: int

    stake_amount: float
    stake_unit: str
    stake_lock_ref: str
    stake_attestation_verified: bool

    provenance_verified: bool
    trusted_registry_ref: str = ""
    trusted_registry_verified: bool = False


@dataclass(frozen=True)
class OwnershipAssessment:
    schema: str
    state: str
    claim_digest: str
    control_pass: bool
    provenance_pass: bool
    work_pass: bool
    stake_pass: bool
    registry_linked: bool
    legal_title_established: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_ownership(
    evidence: OwnershipEvidence,
    *,
    minimum_work_bits: int = 12,
    minimum_stake: float = 0.0,
    required_stake_unit: Optional[str] = None,
) -> OwnershipAssessment:
    """Assess a PoO claim conservatively.

    The strongest state emitted by this module is REGISTRY_LINKED_OWNERSHIP_CLAIM.
    Even that state does not establish legal title; legal_title_established is
    intentionally always False in this software-only evaluator.
    """
    if minimum_work_bits < 0 or minimum_work_bits > 32:
        raise ValueError("minimum_work_bits must be between 0 and 32")
    if minimum_stake < 0:
        raise ValueError("minimum_stake must be non-negative")

    digest = ownership_claim_digest(
        asset_id=evidence.asset_id,
        claimant_id=evidence.claimant_id,
        key_fingerprint=evidence.key_fingerprint,
        provenance_ref=evidence.provenance_ref,
    )

    control_pass = bool(evidence.control_verified and evidence.control_challenge_ref)
    provenance_pass = bool(evidence.provenance_verified and evidence.provenance_ref)
    work_pass = (
        evidence.work_difficulty_bits >= minimum_work_bits
        and verify_work(
            claim_digest=digest,
            nonce=evidence.work_nonce,
            difficulty_bits=evidence.work_difficulty_bits,
        )
    )
    unit_pass = required_stake_unit is None or evidence.stake_unit == required_stake_unit
    stake_pass = bool(
        evidence.stake_attestation_verified
        and evidence.stake_lock_ref
        and evidence.stake_amount >= minimum_stake
        and unit_pass
    )
    registry_linked = bool(
        evidence.trusted_registry_ref
        and evidence.trusted_registry_verified
        and provenance_pass
    )

    reasons: list[str] = []
    if not control_pass:
        reasons.append("claimant control evidence is absent or unverified")
    if not provenance_pass:
        reasons.append("asset provenance linkage is absent or unverified")
    if not work_pass:
        reasons.append("proof-of-work anti-spam gate did not meet policy")
    if not stake_pass:
        reasons.append("bonded proof-of-stake accountability gate did not meet policy")

    if not all((control_pass, provenance_pass, work_pass, stake_pass)):
        state = "INSUFFICIENT_OWNERSHIP_EVIDENCE"
    elif registry_linked:
        state = "REGISTRY_LINKED_OWNERSHIP_CLAIM"
        reasons.append("trusted registry evidence is linked; legal title remains external")
    else:
        state = "BONDED_CRYPTOGRAPHIC_OWNERSHIP_CLAIM"
        reasons.append("cryptographic/provenance claim passes; legal title remains external")

    return OwnershipAssessment(
        schema=POO_SCHEMA,
        state=state,
        claim_digest=digest,
        control_pass=control_pass,
        provenance_pass=provenance_pass,
        work_pass=work_pass,
        stake_pass=stake_pass,
        registry_linked=registry_linked,
        legal_title_established=False,
        reasons=tuple(reasons),
    )
