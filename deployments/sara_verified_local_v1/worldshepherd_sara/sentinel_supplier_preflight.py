from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationState(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SupplierReadinessInput(BaseModel):
    profile_id: str = Field(min_length=1)
    exact_legal_entity: VerificationState = VerificationState.UNVERIFIED
    sam_registration: VerificationState = VerificationState.UNVERIFIED
    uei: VerificationState = VerificationState.UNVERIFIED
    cage: VerificationState = VerificationState.UNVERIFIED
    size_status: VerificationState = VerificationState.UNVERIFIED
    supplier_route: VerificationState = VerificationState.VERIFIED
    nonconfidential_capability_packet: VerificationState = VerificationState.VERIFIED
    internal_software_evidence: VerificationState = VerificationState.VERIFIED
    claims_boundary: VerificationState = VerificationState.VERIFIED
    insurance_applicability: VerificationState = VerificationState.UNVERIFIED
    bonding_applicability: VerificationState = VerificationState.UNVERIFIED
    quality_program: VerificationState = VerificationState.UNVERIFIED
    controlled_information_boundary: VerificationState = VerificationState.UNVERIFIED
    comparable_completed_projects: int = Field(default=0, ge=0)
    design_builder_qualification: VerificationState = VerificationState.UNVERIFIED
    construction_bonding_capacity: VerificationState = VerificationState.UNVERIFIED
    construction_execution_capacity: VerificationState = VerificationState.UNVERIFIED
    cre1aws_external_action_approval: bool = False


TECHNICAL_REVIEW_FIELDS = (
    "supplier_route",
    "nonconfidential_capability_packet",
    "internal_software_evidence",
    "claims_boundary",
)

FEDERAL_ENTITY_FIELDS = (
    "exact_legal_entity",
    "sam_registration",
    "uei",
    "cage",
    "size_status",
)

PRIME_CONSTRUCTION_FIELDS = (
    "design_builder_qualification",
    "construction_bonding_capacity",
    "construction_execution_capacity",
)

CLAIMS_BOUNDARY = (
    "Supplier preflight is an internal evidence-control decision aid. VERIFIED means only that documentary "
    "evidence was supplied to the preflight for the named field; it does not independently authenticate the "
    "document, establish government registration, prime approval, eligibility, certification, clearance, "
    "award probability, or operational readiness."
)


def _all_verified(profile: SupplierReadinessInput, fields: tuple[str, ...]) -> bool:
    return all(getattr(profile, field) == VerificationState.VERIFIED for field in fields)


def evaluate_supplier_preflight(profile: SupplierReadinessInput) -> dict[str, Any]:
    technical_review_ready = _all_verified(profile, TECHNICAL_REVIEW_FIELDS)
    federal_entity_ready = _all_verified(profile, FEDERAL_ENTITY_FIELDS)
    direct_prime_evidence_ready = (
        profile.comparable_completed_projects >= 2
        and _all_verified(profile, PRIME_CONSTRUCTION_FIELDS)
    )

    missing_or_unverified = sorted(
        field
        for field, value in profile.model_dump(mode="json").items()
        if value in {VerificationState.MISSING.value, VerificationState.UNVERIFIED.value}
    )

    partner_packet_review_ready = technical_review_ready
    supplier_registration_ready = technical_review_ready and federal_entity_ready
    external_supplier_submission_authorized = (
        supplier_registration_ready and profile.cre1aws_external_action_approval
    )

    direct_prime_route = "NO_GO" if not direct_prime_evidence_ready else "EVIDENCE_REVIEW_REQUIRED"
    partner_route = "READY_FOR_INTERNAL_REVIEW" if partner_packet_review_ready else "NOT_READY"

    return {
        "schema": "WS-SENTINEL-SUPPLIER-PREFLIGHT-V1",
        "profile_id": profile.profile_id,
        "technical_review_ready": technical_review_ready,
        "federal_entity_ready": federal_entity_ready,
        "supplier_registration_ready": supplier_registration_ready,
        "external_supplier_submission_authorized": external_supplier_submission_authorized,
        "direct_prime_evidence_ready": direct_prime_evidence_ready,
        "direct_prime_route": direct_prime_route,
        "partner_route": partner_route,
        "missing_or_unverified_fields": missing_or_unverified,
        "decision": (
            "PARTNER_PACKET_READY_EXTERNAL_ACTION_BLOCKED"
            if partner_packet_review_ready and not external_supplier_submission_authorized
            else "EXTERNAL_SUPPLIER_SUBMISSION_AUTHORIZED"
            if external_supplier_submission_authorized
            else "INTERNAL_PREPARATION_INCOMPLETE"
        ),
        "claims_boundary": CLAIMS_BOUNDARY,
    }


def default_unverified_profile() -> SupplierReadinessInput:
    return SupplierReadinessInput(profile_id="WS-SENTINEL-SUPPLIER-DEFAULT")
