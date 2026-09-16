"""Worldshepherd measured-PoW -> applied-work -> PoS application bridge.

Worldshepherd terminology in this module is deliberately distinct from ordinary
blockchain shorthand:

    measured proof of work -> validated applied-work receipt -> bounded PoS application

Here, WS-PoW is evidence that work was actually executed and measured. WS-PoS is
the subsequent application of that validated work in a bounded consensus/use
context. It may consume only measured work already represented by the receipt.
It may not invent, amplify, or rewrite the upstream measurement evidence.

Referenced production Proof-of-Stake networks remain reference adapters only.
This bridge does not claim that those networks implement Worldshepherd Applied
Work Theory or that their native stake/economic semantics are equivalent to
Worldshepherd's post-PoW application semantics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from security.qcrypto.applied_work_postwork import (
    AppliedWorkReceipt,
    PostWorkStakePosition,
    stake_eligible,
    verify_post_work_preservation,
)
from security.qcrypto.pos_family_preservation import PROFILES
from security.qcrypto.qpos_preservation import AuthMode, ValidatorState


@dataclass(frozen=True)
class AppliedWorkValidatorApplication:
    validator: ValidatorState
    work_id: str
    contributor_id: str
    evidence_digest: str
    consensus_domain: str
    epoch: int
    measured_work_units: int
    source_validation_state: str
    application_claim: str = "WORLDSHEPHERD_POST_POW_APPLIED_WORK_POS_APPLICATION"


@dataclass(frozen=True)
class FamilyApplicationProjection:
    profile_id: str
    network: str
    consensus_family: str
    weight_semantics: str
    normalized_post_work_weight: int
    work_id: str
    evidence_digest: str
    measured_work_units: int
    source_validation_state: str
    application_mode: str = "WORLDSHEPHERD_REFERENCE_ADAPTER_ONLY"
    production_network_adoption_claimed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def instantiate_validator_application(
    receipt: AppliedWorkReceipt,
    position: PostWorkStakePosition,
    *,
    validator_id: str,
    withdrawal_owner: str,
    classical_credential: str,
) -> AppliedWorkValidatorApplication:
    """Apply already measured/validated work to a bounded PoS validator context.

    This is intentionally downstream-only: the PoS application is refused unless
    the receipt is already stake-eligible under the measured-work evidence gate.
    """

    if not stake_eligible(receipt):
        raise ValueError("PoS application requires measured, validated applied work")
    if receipt.work_id != position.work_id:
        raise ValueError("work_id lineage mismatch")
    if receipt.contributor_id != position.contributor_id:
        raise ValueError("contributor lineage mismatch")
    if receipt.evidence_digest != position.evidence_digest:
        raise ValueError("evidence lineage mismatch")
    if position.stake_units > receipt.validated_work_units:
        raise ValueError("validator stake exceeds measured applied work")

    slashing_history = ()
    if position.slashed_units:
        slashing_history = (f"POST_WORK_SLASH_UNITS:{position.slashed_units}",)

    validator = ValidatorState(
        validator_id=validator_id,
        stake=position.stake_units,
        effective_balance=position.active_stake_units,
        withdrawal_owner=withdrawal_owner,
        slashed=position.slashed_units > 0,
        slashing_history=slashing_history,
        classical_credential=classical_credential,
        pq_credential=position.pq_credential_id,
        pq_scheme=None,
        auth_mode=AuthMode.CLASSICAL,
    )
    return AppliedWorkValidatorApplication(
        validator=validator,
        work_id=receipt.work_id,
        contributor_id=receipt.contributor_id,
        evidence_digest=receipt.evidence_digest,
        consensus_domain=position.consensus_domain,
        epoch=position.epoch,
        measured_work_units=receipt.validated_work_units,
        source_validation_state=receipt.validation_state.value,
    )


def verify_application_lineage(
    receipt: AppliedWorkReceipt,
    position: PostWorkStakePosition,
    application: AppliedWorkValidatorApplication,
) -> None:
    """Prove that PoS application remains subordinate to its measured PoW record."""

    # A no-op preservation comparison still checks the protected work lineage and
    # stake conservation invariants at the application boundary.
    verify_post_work_preservation(receipt, position, position)
    validator = application.validator
    if application.work_id != receipt.work_id or position.work_id != receipt.work_id:
        raise ValueError("work lineage was not preserved")
    if application.contributor_id != receipt.contributor_id:
        raise ValueError("contributor lineage was not preserved")
    if application.evidence_digest != receipt.evidence_digest:
        raise ValueError("evidence lineage was not preserved")
    if application.measured_work_units != receipt.validated_work_units:
        raise ValueError("measured PoW quantity lineage was not preserved")
    if application.source_validation_state != receipt.validation_state.value:
        raise ValueError("source PoW validation-state lineage was not preserved")
    if validator.stake != position.stake_units:
        raise ValueError("PoS application changed allocated stake units")
    if validator.effective_balance != position.active_stake_units:
        raise ValueError("PoS application changed active stake units")
    if validator.stake > application.measured_work_units:
        raise ValueError("PoS application amplified weight beyond measured PoW")


def project_to_family(
    application: AppliedWorkValidatorApplication,
    *,
    profile_id: str,
) -> FamilyApplicationProjection:
    try:
        profile = PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown PoS reference profile: {profile_id}") from exc

    return FamilyApplicationProjection(
        profile_id=profile.profile_id,
        network=profile.network,
        consensus_family=profile.consensus_family,
        weight_semantics=profile.weight_semantics,
        normalized_post_work_weight=application.validator.effective_balance,
        work_id=application.work_id,
        evidence_digest=application.evidence_digest,
        measured_work_units=application.measured_work_units,
        source_validation_state=application.source_validation_state,
    )


def project_to_all_families(
    application: AppliedWorkValidatorApplication,
) -> dict[str, FamilyApplicationProjection]:
    return {
        profile_id: project_to_family(application, profile_id=profile_id)
        for profile_id in PROFILES
    }


def validate_application_registry(applications: Iterable[AppliedWorkValidatorApplication]) -> None:
    apps = tuple(applications)
    validator_ids = [app.validator.validator_id for app in apps]
    if len(set(validator_ids)) != len(validator_ids):
        raise ValueError("validator identities must be unique")

    work_slots = [(app.work_id, app.consensus_domain, app.epoch) for app in apps]
    if len(set(work_slots)) != len(work_slots):
        raise ValueError("one applied-work receipt cannot create multiple validator weights in one domain/epoch")

    for app in apps:
        if app.measured_work_units <= 0:
            raise ValueError("PoS application requires positive measured PoW units")
        if not app.source_validation_state:
            raise ValueError("PoS application requires source PoW validation state")
        if app.validator.stake > app.measured_work_units:
            raise ValueError("PoS application exceeds measured PoW units")
        if app.validator.effective_balance > app.validator.stake:
            raise ValueError("effective validator weight exceeds allocated post-work stake")
