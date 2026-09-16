"""Applied Work -> post-work Proof-of-Stake application model.

This module treats stake as an application-layer allocation over already validated
work evidence. It does not assign economic value to work and does not claim that
existing production PoS networks use this model.

Core boundary:
    applied work is evidenced first; post-work stake may consume that evidence,
    but consensus operations may never rewrite the underlying work record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Iterable


class WorkValidationState(str, Enum):
    UNVALIDATED = "UNVALIDATED"
    IMPLEMENTED_IN_SOFTWARE = "IMPLEMENTED_IN_SOFTWARE"
    PROVEN_INTERNALLY = "PROVEN_INTERNALLY"
    INDEPENDENTLY_REPRODUCED = "INDEPENDENTLY_REPRODUCED"


@dataclass(frozen=True)
class AppliedWorkReceipt:
    work_id: str
    contributor_id: str
    evidence_digest: str
    validated_work_units: int
    validation_state: WorkValidationState
    evidence_retained: bool
    reproducible: bool
    safety_authorized: bool
    measurement_accessible: bool
    revoked: bool = False


@dataclass(frozen=True)
class PostWorkStakePosition:
    work_id: str
    contributor_id: str
    consensus_domain: str
    epoch: int
    evidence_digest: str
    stake_units: int
    active_stake_units: int
    slashed_units: int = 0
    pq_credential_id: str | None = None


@dataclass(frozen=True)
class PostWorkProofReport:
    status: str
    claim_state: str
    receipts_checked: int
    applications_checked: int
    proven_properties: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["proven_properties"] = list(self.proven_properties)
        data["excluded_claims"] = list(self.excluded_claims)
        return data


ELIGIBLE_VALIDATION_STATES = {
    WorkValidationState.PROVEN_INTERNALLY,
    WorkValidationState.INDEPENDENTLY_REPRODUCED,
}


def validate_receipt(receipt: AppliedWorkReceipt) -> None:
    if not receipt.work_id or not receipt.contributor_id:
        raise ValueError("stable work and contributor identifiers are required")
    if len(receipt.evidence_digest) != 64:
        raise ValueError("evidence_digest must be a 64-character SHA-256 hex digest")
    try:
        int(receipt.evidence_digest, 16)
    except ValueError as exc:
        raise ValueError("evidence_digest must be hexadecimal") from exc
    if receipt.validated_work_units <= 0:
        raise ValueError("validated_work_units must be positive")


def stake_eligible(receipt: AppliedWorkReceipt) -> bool:
    validate_receipt(receipt)
    return (
        receipt.validation_state in ELIGIBLE_VALIDATION_STATES
        and receipt.evidence_retained
        and receipt.reproducible
        and receipt.safety_authorized
        and receipt.measurement_accessible
        and not receipt.revoked
    )


def apply_post_work_stake(
    receipt: AppliedWorkReceipt,
    *,
    consensus_domain: str,
    epoch: int,
    requested_stake_units: int,
    existing_positions: Iterable[PostWorkStakePosition] = (),
    pq_credential_id: str | None = None,
) -> PostWorkStakePosition:
    """Create one bounded stake application from an already validated work receipt.

    The model refuses to derive more stake units than the receipt's externally
    validated work units and refuses duplicate use of the same work receipt in the
    same consensus domain/epoch. It does not determine monetary value.
    """

    validate_receipt(receipt)
    if not stake_eligible(receipt):
        raise ValueError("applied work is not eligible for post-work stake")
    if not consensus_domain:
        raise ValueError("consensus_domain is required")
    if epoch < 0:
        raise ValueError("epoch must be non-negative")
    if requested_stake_units <= 0:
        raise ValueError("requested_stake_units must be positive")
    if requested_stake_units > receipt.validated_work_units:
        raise ValueError("post-work stake cannot exceed validated applied-work units")

    for position in existing_positions:
        if (
            position.work_id == receipt.work_id
            and position.consensus_domain == consensus_domain
            and position.epoch == epoch
        ):
            raise ValueError("applied-work receipt already used in this consensus domain/epoch")

    return PostWorkStakePosition(
        work_id=receipt.work_id,
        contributor_id=receipt.contributor_id,
        consensus_domain=consensus_domain,
        epoch=epoch,
        evidence_digest=receipt.evidence_digest,
        stake_units=requested_stake_units,
        active_stake_units=requested_stake_units,
        pq_credential_id=pq_credential_id,
    )


def slash_position(position: PostWorkStakePosition, slash_units: int) -> PostWorkStakePosition:
    """Reduce active stake without altering the upstream proof-of-work identity."""

    if slash_units <= 0:
        raise ValueError("slash_units must be positive")
    if slash_units > position.active_stake_units:
        raise ValueError("slash_units cannot exceed active stake")
    return replace(
        position,
        active_stake_units=position.active_stake_units - slash_units,
        slashed_units=position.slashed_units + slash_units,
    )


def rotate_pq_credential(position: PostWorkStakePosition, pq_credential_id: str) -> PostWorkStakePosition:
    if not pq_credential_id:
        raise ValueError("pq_credential_id is required")
    return replace(position, pq_credential_id=pq_credential_id)


def verify_post_work_preservation(
    receipt: AppliedWorkReceipt,
    before: PostWorkStakePosition,
    after: PostWorkStakePosition,
) -> None:
    """Verify that post-work consensus operations did not rewrite applied-work proof."""

    validate_receipt(receipt)
    immutable_pairs = (
        (before.work_id, after.work_id, receipt.work_id, "work_id"),
        (before.contributor_id, after.contributor_id, receipt.contributor_id, "contributor_id"),
        (before.evidence_digest, after.evidence_digest, receipt.evidence_digest, "evidence_digest"),
        (before.stake_units, after.stake_units, before.stake_units, "stake_units"),
        (before.consensus_domain, after.consensus_domain, before.consensus_domain, "consensus_domain"),
        (before.epoch, after.epoch, before.epoch, "epoch"),
    )
    for left, right, expected, name in immutable_pairs:
        if left != expected or right != expected:
            raise ValueError(f"post-work operation mutated protected field: {name}")

    if before.stake_units > receipt.validated_work_units or after.stake_units > receipt.validated_work_units:
        raise ValueError("stake amplification beyond validated applied work detected")
    if after.active_stake_units < 0:
        raise ValueError("active stake cannot be negative")
    if after.active_stake_units + after.slashed_units != after.stake_units:
        raise ValueError("slashing conservation invariant violated")


def run_bounded_post_work_proof() -> PostWorkProofReport:
    """Run a deterministic bounded proof over representative validation/application states."""

    receipts_checked = 0
    applications_checked = 0

    for state in WorkValidationState:
        for retained in (False, True):
            for reproducible in (False, True):
                for authorized in (False, True):
                    for measurable in (False, True):
                        for revoked in (False, True):
                            receipt = AppliedWorkReceipt(
                                work_id=f"work-{state.value}-{retained}-{reproducible}-{authorized}-{measurable}-{revoked}",
                                contributor_id="contributor-A",
                                evidence_digest="ab" * 32,
                                validated_work_units=100,
                                validation_state=state,
                                evidence_retained=retained,
                                reproducible=reproducible,
                                safety_authorized=authorized,
                                measurement_accessible=measurable,
                                revoked=revoked,
                            )
                            receipts_checked += 1
                            eligible = stake_eligible(receipt)
                            expected = (
                                state in ELIGIBLE_VALIDATION_STATES
                                and retained
                                and reproducible
                                and authorized
                                and measurable
                                and not revoked
                            )
                            if eligible != expected:
                                raise AssertionError("eligibility invariant failed")

    base = AppliedWorkReceipt(
        work_id="validated-work-1",
        contributor_id="contributor-A",
        evidence_digest="cd" * 32,
        validated_work_units=100,
        validation_state=WorkValidationState.PROVEN_INTERNALLY,
        evidence_retained=True,
        reproducible=True,
        safety_authorized=True,
        measurement_accessible=True,
    )

    for requested in (1, 25, 50, 100):
        position = apply_post_work_stake(
            base,
            consensus_domain="WS-QPOS",
            epoch=1,
            requested_stake_units=requested,
            pq_credential_id="pq-credential-1",
        )
        applications_checked += 1
        rotated = rotate_pq_credential(position, "pq-credential-2")
        verify_post_work_preservation(base, position, rotated)
        if requested > 1:
            slashed = slash_position(rotated, 1)
            verify_post_work_preservation(base, rotated, slashed)

    try:
        apply_post_work_stake(
            base,
            consensus_domain="WS-QPOS",
            epoch=1,
            requested_stake_units=101,
        )
    except ValueError:
        applications_checked += 1
    else:
        raise AssertionError("stake amplification was not rejected")

    first = apply_post_work_stake(
        base,
        consensus_domain="WS-QPOS",
        epoch=2,
        requested_stake_units=50,
    )
    try:
        apply_post_work_stake(
            base,
            consensus_domain="WS-QPOS",
            epoch=2,
            requested_stake_units=50,
            existing_positions=(first,),
        )
    except ValueError:
        applications_checked += 1
    else:
        raise AssertionError("duplicate work receipt use was not rejected")

    return PostWorkProofReport(
        status="PASS",
        claim_state="BOUNDED_MODEL_PROOF_OF_APPLIED_WORK_TO_POST_WORK_STAKE_PRESERVATION",
        receipts_checked=receipts_checked,
        applications_checked=applications_checked,
        proven_properties=(
            "stake requires retained, reproducible, safety-authorized, measurable validated work evidence",
            "post-work stake cannot exceed externally validated applied-work units",
            "one work receipt cannot be counted twice in the same consensus domain/epoch",
            "PQ credential rotation cannot rewrite upstream work proof or stake allocation",
            "slashing reduces active stake without erasing or rewriting applied-work evidence",
        ),
        excluded_claims=(
            "economic valuation of applied work",
            "production-network adoption",
            "legal ownership or securities status",
            "post-quantum primitive security",
            "production consensus security",
        ),
    )
