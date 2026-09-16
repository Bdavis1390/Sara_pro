"""Recursive Worldshepherd measured-PoW -> PoS application validation cycle.

The cycle is claims-controlled and deliberately distinct from ordinary blockchain
consensus shorthand:

    executed work
        -> measured proof-of-work evidence
        -> validated applied-work certificate
        -> bounded WS-PoS application
        -> measured application outcome
        -> candidate evidence for a later cycle

A PoS application never self-certifies. Its authority comes from upstream measured
PoW evidence, and any later promotion requires new measured outcome evidence.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from security.qcrypto.applied_work_postwork import PostWorkStakePosition
from security.qcrypto.applied_work_pos_application import (
    AppliedWorkValidatorApplication,
    verify_application_lineage,
)
from security.qcrypto.applied_work_proof import (
    AppliedWorkCertificate,
    AppliedWorkProofState,
    certificate_to_postwork_receipt,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AppliedWorkCycleRecord:
    cycle_id: str
    work_id: str
    contributor_id: str
    evidence_digest: str
    pow_measured_units: int
    pow_state: str
    pos_applied_units: int
    consensus_domain: str
    epoch: int
    validator_id: str
    status: str = "POS_APPLICATION_OF_MEASURED_POW"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PostApplicationMeasurement:
    name: str
    measured_units: int
    source_sha256: str
    passed: bool


@dataclass(frozen=True)
class CycleClosure:
    cycle_id: str
    work_id: str
    application_measurement_count: int
    passed_measurement_count: int
    failed_measurement_count: int
    measured_outcome_units: int
    next_pow_candidate: bool
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


_ELIGIBLE_POW_STATES = {
    AppliedWorkProofState.PRESERVED_APPLIED_WORK,
    AppliedWorkProofState.INDEPENDENTLY_REPRODUCED,
}


def open_pos_application_cycle(
    certificate: AppliedWorkCertificate,
    position: PostWorkStakePosition,
    application: AppliedWorkValidatorApplication,
    *,
    cycle_id: str,
) -> AppliedWorkCycleRecord:
    """Bind one WS-PoS application to a preserved measured-PoW certificate."""

    if not cycle_id:
        raise ValueError("cycle_id is required")
    if certificate.proof_state not in _ELIGIBLE_POW_STATES:
        raise ValueError("PoS application cycle requires preserved measured PoW evidence")
    if certificate.measured_work_units <= 0:
        raise ValueError("PoS application cycle requires positive measured PoW units")

    receipt = certificate_to_postwork_receipt(certificate)
    verify_application_lineage(receipt, position, application)

    if application.evidence_digest != certificate.evidence_digest:
        raise ValueError("PoS application does not bind to the measured PoW evidence digest")
    if application.measured_work_units != certificate.measured_work_units:
        raise ValueError("PoS application does not preserve the measured PoW quantity")
    if application.validator.effective_balance > certificate.measured_work_units:
        raise ValueError("PoS application exceeds measured PoW capacity")

    return AppliedWorkCycleRecord(
        cycle_id=cycle_id,
        work_id=certificate.work_id,
        contributor_id=certificate.contributor_id,
        evidence_digest=certificate.evidence_digest,
        pow_measured_units=certificate.measured_work_units,
        pow_state=certificate.proof_state.value,
        pos_applied_units=application.validator.effective_balance,
        consensus_domain=application.consensus_domain,
        epoch=application.epoch,
        validator_id=application.validator.validator_id,
    )


def close_pos_application_cycle(
    cycle: AppliedWorkCycleRecord,
    measurements: Iterable[PostApplicationMeasurement],
) -> CycleClosure:
    """Measure the applied result; do not auto-promote it into a new PoW claim."""

    values = tuple(measurements)
    if not values:
        raise ValueError("at least one post-application measurement is required")

    for item in values:
        if not item.name:
            raise ValueError("post-application measurement name is required")
        if item.measured_units <= 0:
            raise ValueError("post-application measured_units must be positive")
        if not _SHA256.fullmatch(item.source_sha256):
            raise ValueError("post-application source_sha256 must be a lowercase SHA-256 digest")

    passed = tuple(item for item in values if item.passed)
    failed = len(values) - len(passed)
    outcome_units = sum(item.measured_units for item in passed)
    next_pow_candidate = failed == 0 and outcome_units > 0

    return CycleClosure(
        cycle_id=cycle.cycle_id,
        work_id=cycle.work_id,
        application_measurement_count=len(values),
        passed_measurement_count=len(passed),
        failed_measurement_count=failed,
        measured_outcome_units=outcome_units,
        next_pow_candidate=next_pow_candidate,
        status=(
            "POST_APPLICATION_MEASURED_CANDIDATE_FOR_NEXT_POW"
            if next_pow_candidate
            else "POST_APPLICATION_MEASURED_NOT_PROMOTABLE"
        ),
    )
