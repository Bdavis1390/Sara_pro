"""Worldshepherd Applied Work -> post-work PoS application bridge.

The bridge makes the ordering explicit:

    validated applied work -> bounded post-work stake -> PoS validator application

PoS is therefore an application of already evidenced work in this Worldshepherd
model. The bridge never infers economic value and does not claim that referenced
production networks implement Applied Work Theory.
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
    application_claim: str = "WORLDSHEPHERD_POST_WORK_POS_APPLICATION"


@dataclass(frozen=True)
class FamilyApplicationProjection:
    profile_id: str
    network: str
    consensus_family: str
    weight_semantics: str
    normalized_post_work_weight: int
    work_id: str
    evidence_digest: str
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
    if not stake_eligible(receipt):
        raise ValueError("validator application requires stake-eligible applied work")
    if receipt.work_id != position.work_id:
        raise ValueError("work_id lineage mismatch")
    if receipt.contributor_id != position.contributor_id:
        raise ValueError("contributor lineage mismatch")
    if receipt.evidence_digest != position.evidence_digest:
        raise ValueError("evidence lineage mismatch")
    if position.stake_units > receipt.validated_work_units:
        raise ValueError("validator stake exceeds validated applied work")

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
    )


def verify_application_lineage(
    receipt: AppliedWorkReceipt,
    position: PostWorkStakePosition,
    application: AppliedWorkValidatorApplication,
) -> None:
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
    if validator.stake != position.stake_units:
        raise ValueError("PoS application changed allocated stake units")
    if validator.effective_balance != position.active_stake_units:
        raise ValueError("PoS application changed active stake units")


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
        if app.validator.effective_balance > app.validator.stake:
            raise ValueError("effective validator weight exceeds allocated post-work stake")
