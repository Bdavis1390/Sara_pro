from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .prime_configuration_custody import (
    REQUALIFICATION_CHECKS,
    PrimeActivationDisposition,
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
    apply_post_mission_state,
    evaluate_pack_activation,
    missing_requalification_checks,
    release_from_quarantine,
)
from .prime_sentinel_authorization import VerifiedPrimeSentinelAuthorization


PRIME_PASSPORTS_REGISTRY_KEY = "PRIME_DIGITAL_PASSPORTS"
PRIME_CUSTODY_PROVENANCE_SCHEMA = "WS-ECHO-PRIME-CUSTODY-V1"


class PrimeDigitalPassport(BaseModel):
    prime_id: str = Field(min_length=1, max_length=128)
    hardware_revision: str = Field(min_length=1, max_length=128)
    software_revision: str = Field(min_length=1, max_length=128)
    custody: PrimeConfigurationCustodyRecord
    installed_pack: PrimeMissionPackEvidence | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    last_transition_id: str | None = Field(default=None, max_length=128)

    @field_validator("evidence_refs")
    @classmethod
    def evidence_refs_are_bounded(cls, value: list[str]) -> list[str]:
        if len(value) > 128:
            raise ValueError("evidence_refs exceeds 128 entries")
        for item in value:
            if not item or len(item) > 256:
                raise ValueError("each evidence reference must contain 1-256 characters")
        return value


class PrimePassportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hardware_revision: str = Field(min_length=1, max_length=128)
    software_revision: str = Field(min_length=1, max_length=128)
    evidence_refs: list[str] = Field(default_factory=list)


class PrimeMissionCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    environment: PrimeEnvironment
    evidence_refs: list[str] = Field(default_factory=list)


class PrimeRequalificationEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed_checks: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("completed_checks")
    @classmethod
    def checks_are_known_and_unique(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - set(REQUALIFICATION_CHECKS))
        if unknown:
            raise ValueError(f"unknown requalification checks: {', '.join(unknown)}")
        if len(value) != len(set(value)):
            raise ValueError("completed_checks contains duplicates")
        return value


class PrimePackActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack: PrimeMissionPackEvidence
    evidence_refs: list[str] = Field(default_factory=list)


def new_transition_id() -> str:
    return f"PRIME-CUSTODY-{uuid4()}"


def create_passport(
    *,
    prime_id: str,
    hardware_revision: str,
    software_revision: str,
    evidence_refs: list[str] | None = None,
) -> PrimeDigitalPassport:
    return PrimeDigitalPassport(
        prime_id=prime_id,
        hardware_revision=hardware_revision,
        software_revision=software_revision,
        custody=PrimeConfigurationCustodyRecord(prime_id=prime_id),
        evidence_refs=list(evidence_refs or []),
    )


def _passport_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_PASSPORTS_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise ValueError(f"{PRIME_PASSPORTS_REGISTRY_KEY} must be a JSON object")
    return dict(raw)


def load_passport(registry: dict[str, Any], prime_id: str) -> PrimeDigitalPassport | None:
    raw = _passport_map(registry).get(prime_id)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"passport entry for {prime_id} must be a JSON object")
    passport = PrimeDigitalPassport.model_validate(raw)
    if passport.prime_id != prime_id or passport.custody.prime_id != prime_id:
        raise ValueError(f"passport identity mismatch for {prime_id}")
    return passport


def passport_registry_patch(
    registry: dict[str, Any], passport: PrimeDigitalPassport
) -> dict[str, Any]:
    passports = _passport_map(registry)
    passports[passport.prime_id] = passport.model_dump(mode="json")
    return {PRIME_PASSPORTS_REGISTRY_KEY: passports}


def _merge_evidence(existing: list[str], additions: list[str]) -> list[str]:
    merged = list(existing)
    for item in additions:
        if item not in merged:
            merged.append(item)
    return merged


def complete_mission(
    passport: PrimeDigitalPassport,
    request: PrimeMissionCompletionRequest,
) -> tuple[PrimeDigitalPassport, dict[str, Any]]:
    transition_id = new_transition_id()
    previous_state = passport.custody.state.value
    updated_custody = apply_post_mission_state(passport.custody, request.environment)
    updated = passport.model_copy(
        update={
            "custody": updated_custody,
            "installed_pack": None,
            "evidence_refs": _merge_evidence(passport.evidence_refs, request.evidence_refs),
            "last_transition_id": transition_id,
        }
    )
    payload = custody_provenance_payload(
        transition_id=transition_id,
        prime_id=passport.prime_id,
        action="MISSION_COMPLETED",
        previous_state=previous_state,
        new_state=updated.custody.state.value,
        evidence_refs=request.evidence_refs,
        environment=request.environment.value,
    )
    return updated, payload


def update_requalification_evidence(
    passport: PrimeDigitalPassport,
    request: PrimeRequalificationEvidenceRequest,
) -> tuple[PrimeDigitalPassport, dict[str, Any]]:
    transition_id = new_transition_id()
    previous_state = passport.custody.state.value
    updated_custody = passport.custody.model_copy(
        update={
            "completed_requalification_checks": list(request.completed_checks),
            "requalification_release_authorization_id": None,
            "requalification_release_target_environment": None,
            "requalification_release_key_id": None,
        }
    )
    updated = passport.model_copy(
        update={
            "custody": updated_custody,
            "evidence_refs": _merge_evidence(passport.evidence_refs, request.evidence_refs),
            "last_transition_id": transition_id,
        }
    )
    payload = custody_provenance_payload(
        transition_id=transition_id,
        prime_id=passport.prime_id,
        action="REQUALIFICATION_EVIDENCE_UPDATED",
        previous_state=previous_state,
        new_state=updated.custody.state.value,
        evidence_refs=request.evidence_refs,
        completed_checks=list(request.completed_checks),
        prior_authorization_cleared=True,
    )
    return updated, payload


def apply_verified_requalification_authorization(
    passport: PrimeDigitalPassport,
    verified: VerifiedPrimeSentinelAuthorization,
) -> tuple[PrimeDigitalPassport, dict[str, Any]]:
    if passport.prime_id != verified.prime_id:
        raise ValueError("PRIME SENTINEL authorization identity does not match passport")
    if passport.custody.state != PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION:
        raise ValueError("PRIME is not quarantined for requalification")
    missing = missing_requalification_checks(passport.custody)
    if missing:
        raise ValueError("requalification evidence is incomplete")

    transition_id = new_transition_id()
    updated_custody = passport.custody.model_copy(
        update={
            "requalification_release_authorization_id": verified.authorization_id,
            "requalification_release_target_environment": verified.target_environment,
            "requalification_release_key_id": verified.key_id,
        }
    )
    updated = passport.model_copy(
        update={
            "custody": updated_custody,
            "last_transition_id": transition_id,
        }
    )
    payload = custody_provenance_payload(
        transition_id=transition_id,
        prime_id=passport.prime_id,
        action="REQUALIFICATION_AUTHORIZATION_VERIFIED",
        previous_state=passport.custody.state.value,
        new_state=updated.custody.state.value,
        evidence_refs=[],
        authorization_id=verified.authorization_id,
        target_environment=verified.target_environment.value,
        key_id=verified.key_id,
        key_fingerprint_sha256=verified.key_fingerprint_sha256,
        expires_at=verified.expires_at.isoformat(),
    )
    return updated, payload


def activate_pack(
    passport: PrimeDigitalPassport,
    request: PrimePackActivationRequest,
) -> tuple[PrimeDigitalPassport, PrimeActivationDisposition, list[str], dict[str, Any]]:
    transition_id = new_transition_id()
    previous_state = passport.custody.state.value
    disposition, reasons = evaluate_pack_activation(passport.custody, request.pack)
    updated = passport

    if disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED:
        released_custody, _, _ = release_from_quarantine(passport.custody, request.pack)
        updated = passport.model_copy(
            update={
                "custody": released_custody,
                "installed_pack": request.pack,
                "evidence_refs": _merge_evidence(passport.evidence_refs, request.evidence_refs),
                "last_transition_id": transition_id,
            }
        )

    payload = custody_provenance_payload(
        transition_id=transition_id,
        prime_id=passport.prime_id,
        action="PACK_ACTIVATION_EVALUATED",
        previous_state=previous_state,
        new_state=updated.custody.state.value,
        evidence_refs=request.evidence_refs,
        authorization_id=passport.custody.requalification_release_authorization_id,
        authorization_key_id=passport.custody.requalification_release_key_id,
        pack_id=request.pack.pack_id,
        target_environment=request.pack.target_environment.value,
        disposition=disposition.value,
        reasons=reasons,
    )
    return updated, disposition, reasons, payload


def custody_provenance_payload(
    *,
    transition_id: str,
    prime_id: str,
    action: str,
    previous_state: str,
    new_state: str,
    evidence_refs: list[str],
    **details: Any,
) -> dict[str, Any]:
    return {
        "schema": PRIME_CUSTODY_PROVENANCE_SCHEMA,
        "provenance_channel": "SARA_AUDIT_FOR_ECHO_INGEST",
        "transition_id": transition_id,
        "prime_id": prime_id,
        "action": action,
        "previous_state": previous_state,
        "new_state": new_state,
        "evidence_refs": list(evidence_refs),
        "details": details,
        "claims_boundary": (
            "Software custody/provenance evidence only; does not establish physical "
            "mine, deep-sea, flight, launch, or space qualification."
        ),
    }
