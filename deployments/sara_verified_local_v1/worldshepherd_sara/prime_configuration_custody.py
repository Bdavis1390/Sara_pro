from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PrimeEnvironment(str, Enum):
    GROUND = "GROUND"
    SUBTERRA = "SUBTERRA"
    HADAL = "HADAL"
    AERO = "AERO"
    SPACE = "SPACE"


class PrimeCustodyState(str, Enum):
    READY = "READY"
    QUARANTINED_FOR_REQUALIFICATION = "QUARANTINED_FOR_REQUALIFICATION"


class PrimeActivationDisposition(str, Enum):
    ACTIVATION_ALLOWED = "ACTIVATION_ALLOWED"
    REQUALIFICATION_REQUIRED = "REQUALIFICATION_REQUIRED"
    DENIED = "DENIED"


REQUALIFICATION_CHECKS: tuple[str, ...] = (
    "DECONTAMINATION_CLEANING",
    "MECHANICAL_INSPECTION",
    "CONNECTOR_INSULATION_CHECK",
    "SEAL_TRIBOLOGY_CONDITION",
    "BATTERY_HEALTH",
    "STRUCTURAL_HEALTH_REVIEW",
    "PACK_PROVENANCE",
    "TARGET_ENVIRONMENT_ACCEPTANCE",
)

HAZARDOUS_POST_MISSION_ENVIRONMENTS: frozenset[PrimeEnvironment] = frozenset(
    {PrimeEnvironment.SUBTERRA, PrimeEnvironment.HADAL}
)


class PrimeConfigurationCustodyRecord(BaseModel):
    prime_id: str = Field(min_length=1)
    state: PrimeCustodyState = PrimeCustodyState.READY
    last_environment: PrimeEnvironment = PrimeEnvironment.GROUND
    completed_requalification_checks: list[str] = Field(default_factory=list)
    requalification_release_authorization_id: str | None = None


class PrimeMissionPackEvidence(BaseModel):
    pack_id: str = Field(min_length=1)
    target_environment: PrimeEnvironment
    authenticated: bool = False
    compatible_with_prime: bool = False
    target_environment_qualification_valid: bool = False


def post_mission_state(environment: PrimeEnvironment) -> PrimeCustodyState:
    if environment in HAZARDOUS_POST_MISSION_ENVIRONMENTS:
        return PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    return PrimeCustodyState.READY


def apply_post_mission_state(
    record: PrimeConfigurationCustodyRecord,
    environment: PrimeEnvironment,
) -> PrimeConfigurationCustodyRecord:
    return record.model_copy(
        update={
            "last_environment": environment,
            "state": post_mission_state(environment),
            "completed_requalification_checks": [],
            "requalification_release_authorization_id": None,
        }
    )


def missing_requalification_checks(record: PrimeConfigurationCustodyRecord) -> list[str]:
    completed = set(record.completed_requalification_checks)
    return [check for check in REQUALIFICATION_CHECKS if check not in completed]


def evaluate_pack_activation(
    record: PrimeConfigurationCustodyRecord,
    pack: PrimeMissionPackEvidence,
) -> tuple[PrimeActivationDisposition, list[str]]:
    reasons: list[str] = []

    if not pack.authenticated:
        reasons.append("mission pack identity is not authenticated")
    if not pack.compatible_with_prime:
        reasons.append("mission pack is not compatible with this PRIME")
    if not pack.target_environment_qualification_valid:
        reasons.append("target-environment qualification is not valid")

    if reasons:
        return PrimeActivationDisposition.DENIED, reasons

    if record.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION:
        missing = missing_requalification_checks(record)
        if missing:
            return PrimeActivationDisposition.REQUALIFICATION_REQUIRED, [
                "PRIME remains quarantined after hazardous/deep-environment service",
                *[f"missing requalification check: {check}" for check in missing],
            ]
        if not record.requalification_release_authorization_id:
            return PrimeActivationDisposition.REQUALIFICATION_REQUIRED, [
                "requalification evidence is complete but no release authorization record is present"
            ]

    return PrimeActivationDisposition.ACTIVATION_ALLOWED, [
        "pack authentication, compatibility, target qualification, requalification evidence, and authorization gates are satisfied"
    ]


def release_from_quarantine(
    record: PrimeConfigurationCustodyRecord,
    pack: PrimeMissionPackEvidence,
) -> tuple[PrimeConfigurationCustodyRecord, PrimeActivationDisposition, list[str]]:
    disposition, reasons = evaluate_pack_activation(record, pack)
    if disposition != PrimeActivationDisposition.ACTIVATION_ALLOWED:
        return record, disposition, reasons

    if record.state != PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION:
        return record, disposition, reasons

    released = record.model_copy(update={"state": PrimeCustodyState.READY})
    return released, disposition, reasons
